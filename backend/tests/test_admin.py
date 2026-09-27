def test_non_admin_cannot_access_admin_stats(client, register_user):
    session = register_user(email="regular@example.com")
    response = client.get("/admin/stats", headers=session["headers"])
    assert response.status_code == 403


def test_admin_endpoints_require_auth(client):
    response = client.get("/admin/stats")
    assert response.status_code == 401


def test_admin_can_access_stats(client, register_user, make_admin):
    session = register_user(email="admin@example.com")
    make_admin("admin@example.com")

    response = client.get("/admin/stats", headers=session["headers"])
    assert response.status_code == 200
    body = response.json()
    assert body["total_users"] == 1


def test_admin_can_delete_any_property(client, register_user, make_admin):
    owner = register_user(email="listingowner@example.com")
    admin_session = register_user(email="moderator@example.com")
    make_admin("moderator@example.com")

    created = client.post(
        "/properties",
        json={
            "title": "Moderated listing",
            "description": "",
            "location": "Yunusobod",
            "price": 100000,
            "price_unit": "Oy",
        },
        headers=owner["headers"],
    ).json()

    # A regular (non-owner, non-admin) user still can't touch it
    other = register_user(email="bystander@example.com")
    forbidden = client.delete(f"/properties/{created['id']}", headers=other["headers"])
    assert forbidden.status_code == 403

    # But an admin can moderate it away, despite not owning it
    response = client.delete(f"/admin/properties/{created['id']}", headers=admin_session["headers"])
    assert response.status_code == 204


def test_admin_cannot_delete_self(client, register_user, make_admin):
    session = register_user(email="selfdelete@example.com")
    make_admin("selfdelete@example.com")
    user_id = session["user"]["id"]

    response = client.delete(f"/admin/users/{user_id}", headers=session["headers"])
    assert response.status_code == 400
