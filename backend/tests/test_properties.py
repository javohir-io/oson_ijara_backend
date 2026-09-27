def _property_payload(**overrides):
    payload = {
        "title": "Test Uy",
        "description": "Chiroyli uy",
        "location": "Yunusobod",
        "price": 500000,
        "price_unit": "Oy",
        "bedrooms": 2,
        "bathrooms": 1,
        "floor": 3,
        "area": 60,
        "renovation": "Yaxshi",
        "amenities": ["Wi-Fi"],
        "student_friendly": False,
    }
    payload.update(overrides)
    return payload


def test_create_property_requires_auth(client):
    response = client.post("/properties", json=_property_payload())
    assert response.status_code == 401


def test_create_and_list_property(client, register_user):
    session = register_user(email="owner@example.com")
    created = client.post(
        "/properties", json=_property_payload(title="Chiroyli Kvartira"), headers=session["headers"]
    )
    assert created.status_code == 201
    created_body = created.json()
    assert created_body["title"] == "Chiroyli Kvartira"
    assert created_body["owner"]["email"] == "owner@example.com"

    listing = client.get("/properties")
    assert listing.status_code == 200
    data = listing.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == created_body["id"]


def test_get_property_by_id(client, register_user):
    session = register_user(email="owner2@example.com")
    created = client.post("/properties", json=_property_payload(), headers=session["headers"]).json()

    response = client.get(f"/properties/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_missing_property_404s(client):
    response = client.get("/properties/999999")
    assert response.status_code == 404


def test_owner_can_update_their_property(client, register_user):
    session = register_user(email="owner3@example.com")
    created = client.post("/properties", json=_property_payload(), headers=session["headers"]).json()

    response = client.put(f"/properties/{created['id']}", json={"price": 750000}, headers=session["headers"])
    assert response.status_code == 200
    assert response.json()["price"] == 750000


def test_non_owner_cannot_update_property(client, register_user):
    owner = register_user(email="owner4@example.com")
    other = register_user(email="other4@example.com")
    created = client.post("/properties", json=_property_payload(), headers=owner["headers"]).json()

    response = client.put(f"/properties/{created['id']}", json={"price": 1}, headers=other["headers"])
    assert response.status_code == 403


def test_min_price_filter(client, register_user):
    session = register_user(email="filter@example.com")
    client.post("/properties", json=_property_payload(title="Cheap", price=100000), headers=session["headers"])
    client.post("/properties", json=_property_payload(title="Expensive", price=900000), headers=session["headers"])

    response = client.get("/properties", params={"min_price": 500000})
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["items"]]
    assert "Expensive" in titles
    assert "Cheap" not in titles


def test_blank_numeric_filter_is_ignored_not_rejected(client):
    # Regression test: a blank '?min_price=' query param used to cause a
    # 422 instead of being treated as "no filter" — see properties.py's
    # _to_number() helper.
    response = client.get("/properties", params={"min_price": ""})
    assert response.status_code == 200


def test_toggle_save(client, register_user):
    owner = register_user(email="owner5@example.com")
    viewer = register_user(email="viewer5@example.com")
    created = client.post("/properties", json=_property_payload(), headers=owner["headers"]).json()

    first_toggle = client.post(f"/properties/{created['id']}/save", headers=viewer["headers"])
    assert first_toggle.status_code == 200
    assert first_toggle.json()["saved"] is True

    second_toggle = client.post(f"/properties/{created['id']}/save", headers=viewer["headers"])
    assert second_toggle.status_code == 200
    assert second_toggle.json()["saved"] is False


def test_delete_property_owner_only(client, register_user):
    owner = register_user(email="owner6@example.com")
    other = register_user(email="other6@example.com")
    created = client.post("/properties", json=_property_payload(), headers=owner["headers"]).json()

    forbidden = client.delete(f"/properties/{created['id']}", headers=other["headers"])
    assert forbidden.status_code == 403

    ok = client.delete(f"/properties/{created['id']}", headers=owner["headers"])
    assert ok.status_code == 204
