def test_send_message_requires_auth(client):
    response = client.post("/messages", json={"receiver_id": 1, "content": "hi"})
    assert response.status_code == 401


def test_cannot_message_yourself(client, register_user):
    session = register_user(email="lonely@example.com")
    my_id = session["user"]["id"]

    response = client.post(
        "/messages", json={"receiver_id": my_id, "content": "hi me"}, headers=session["headers"]
    )
    assert response.status_code == 400


def test_send_and_fetch_conversation(client, register_user):
    alice = register_user(email="alice.chat@example.com")
    bob = register_user(email="bob.chat@example.com")
    bob_id = bob["user"]["id"]
    alice_id = alice["user"]["id"]

    sent = client.post(
        "/messages", json={"receiver_id": bob_id, "content": "Salom, uy hali bo'shmi?"}, headers=alice["headers"]
    )
    assert sent.status_code == 201
    assert sent.json()["sender_id"] == alice_id
    assert sent.json()["is_read"] is False

    reply = client.post(
        "/messages", json={"receiver_id": alice_id, "content": "Ha, bo'sh!"}, headers=bob["headers"]
    )
    assert reply.status_code == 201

    history = client.get(f"/messages/with/{bob_id}", headers=alice["headers"])
    assert history.status_code == 200
    contents = [m["content"] for m in history.json()]
    assert contents == ["Salom, uy hali bo'shmi?", "Ha, bo'sh!"]


def test_conversations_list_shows_last_message_and_unread_count(client, register_user):
    alice = register_user(email="alice.conv@example.com")
    bob = register_user(email="bob.conv@example.com")
    bob_id = bob["user"]["id"]

    client.post("/messages", json={"receiver_id": bob_id, "content": "first"}, headers=alice["headers"])
    client.post("/messages", json={"receiver_id": bob_id, "content": "second"}, headers=alice["headers"])

    conversations = client.get("/messages/conversations", headers=bob["headers"])
    assert conversations.status_code == 200
    body = conversations.json()
    assert len(body) == 1
    assert body[0]["last_message"]["content"] == "second"
    assert body[0]["unread_count"] == 2

    # Reading the conversation should mark those messages as read
    client.get(f"/messages/with/{alice['user']['id']}", headers=bob["headers"])
    conversations_after = client.get("/messages/conversations", headers=bob["headers"]).json()
    assert conversations_after[0]["unread_count"] == 0
