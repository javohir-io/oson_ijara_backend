from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import SessionLocal, get_db
from ..deps import absolute_url, get_current_user, get_user_from_token
from ..ws_manager import manager

router = APIRouter(prefix="/messages", tags=["Messages"])


@router.get("/conversations", response_model=list[schemas.ConversationOut])
def list_conversations(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    all_messages = (
        db.query(models.Message)
        .filter(or_(models.Message.sender_id == current_user.id, models.Message.receiver_id == current_user.id))
        .order_by(models.Message.created_at.desc())
        .all()
    )

    last_message_by_other: dict[int, models.Message] = {}
    unread_counts: dict[int, int] = {}

    for m in all_messages:
        other_id = m.receiver_id if m.sender_id == current_user.id else m.sender_id
        if other_id not in last_message_by_other:
            last_message_by_other[other_id] = m
        if m.receiver_id == current_user.id and not m.is_read:
            unread_counts[other_id] = unread_counts.get(other_id, 0) + 1

    results: list[schemas.ConversationOut] = []
    for other_id, last_message in last_message_by_other.items():
        other_user = db.query(models.User).filter(models.User.id == other_id).first()
        if not other_user:
            continue
        results.append(
            schemas.ConversationOut(
                other_user=schemas.OwnerOut(
                    id=other_user.id,
                    full_name=other_user.full_name,
                    phone=other_user.phone,
                    avatar_url=absolute_url(request, other_user.avatar_path),
                ),
                last_message=schemas.MessageOut.model_validate(last_message),
                unread_count=unread_counts.get(other_id, 0),
            )
        )

    results.sort(key=lambda c: c.last_message.created_at, reverse=True)
    return results


@router.get("/with/{user_id}", response_model=list[schemas.MessageOut])
def get_conversation(
    user_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(models.Message)
        .filter(
            or_(
                and_(models.Message.sender_id == current_user.id, models.Message.receiver_id == user_id),
                and_(models.Message.sender_id == user_id, models.Message.receiver_id == current_user.id),
            )
        )
        .order_by(models.Message.created_at.asc())
        .all()
    )

    unread = [m for m in conversation if m.receiver_id == current_user.id and not m.is_read]
    if unread:
        for m in unread:
            m.is_read = True
        db.commit()

    return conversation


@router.post("", response_model=schemas.MessageOut, status_code=201)
async def send_message(
    payload: schemas.MessageCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """REST fallback for sending a message (works even without a WebSocket
    connection open) — used by the same conversation the WS endpoint writes
    to, so both paths stay consistent."""
    if payload.receiver_id == current_user.id:
        raise HTTPException(status_code=400, detail="O'zingizga xabar yubora olmaysiz")

    receiver = db.query(models.User).filter(models.User.id == payload.receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

    message = models.Message(
        sender_id=current_user.id,
        receiver_id=payload.receiver_id,
        content=payload.content,
        property_id=payload.property_id,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    await manager.send_to_user(payload.receiver_id, _message_payload(message))
    return message


def _message_payload(message: models.Message) -> dict:
    return {
        "type": "message",
        "id": message.id,
        "sender_id": message.sender_id,
        "receiver_id": message.receiver_id,
        "property_id": message.property_id,
        "content": message.content,
        "is_read": message.is_read,
        "created_at": message.created_at.isoformat(),
    }


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket, token: str | None = Query(default=None)):
    """Real-time chat socket. Browsers can't set custom headers on a
    WebSocket handshake, so auth is passed as a query param instead:
    wss://.../messages/ws?token=<jwt>

    Send: {"receiver_id": 5, "content": "Salom!", "property_id": 12}
    Receive: the same shape back (echoed to you, and pushed to the
    recipient live if they're connected too)."""
    db = SessionLocal()
    try:
        user = get_user_from_token(token, db)
        if user is None:
            await websocket.close(code=4401)
            return

        await manager.connect(user.id, websocket)
        try:
            while True:
                data = await websocket.receive_json()
                receiver_id = data.get("receiver_id")
                content = (data.get("content") or "").strip()
                property_id = data.get("property_id")

                if not receiver_id or not content:
                    await websocket.send_json({"type": "error", "detail": "receiver_id va content talab qilinadi"})
                    continue
                if receiver_id == user.id:
                    await websocket.send_json({"type": "error", "detail": "O'zingizga xabar yubora olmaysiz"})
                    continue

                message = models.Message(
                    sender_id=user.id,
                    receiver_id=receiver_id,
                    content=content,
                    property_id=property_id,
                )
                db.add(message)
                db.commit()
                db.refresh(message)

                payload = _message_payload(message)
                await websocket.send_json(payload)
                await manager.send_to_user(receiver_id, payload)
        except WebSocketDisconnect:
            pass
        except Exception:
            # Malformed client message or a mid-stream error — close cleanly
            # rather than let it crash silently without freeing the slot.
            pass
        finally:
            manager.disconnect(user.id, websocket)
    finally:
        db.close()
