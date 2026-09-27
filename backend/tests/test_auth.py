def test_register_creates_user_and_returns_token(client):
    response = client.post(
        "/auth/register",
        json={"full_name": "Alice Example", "email": "alice@example.com", "password": "supersecret"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["access_token"]
    assert data["user"]["email"] == "alice@example.com"
    assert data["user"]["is_admin"] is False


def test_register_rejects_duplicate_email(client, register_user):
    register_user(email="dup@example.com")
    response = client.post(
        "/auth/register",
        json={"full_name": "Someone Else", "email": "dup@example.com", "password": "anotherpass"},
    )
    assert response.status_code == 400


def test_register_rejects_short_password(client):
    response = client.post(
        "/auth/register",
        json={"full_name": "Short Pass", "email": "short@example.com", "password": "123"},
    )
    assert response.status_code == 422


def test_login_with_correct_credentials(client, register_user):
    register_user(email="login@example.com", password="mypassword1")
    response = client.post("/auth/login", data={"username": "login@example.com", "password": "mypassword1"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_with_wrong_password_fails(client, register_user):
    register_user(email="wrongpass@example.com", password="correctpass")
    response = client.post("/auth/login", data={"username": "wrongpass@example.com", "password": "incorrect"})
    assert response.status_code == 401


def test_me_requires_auth(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user(client, register_user):
    session = register_user(email="me@example.com")
    response = client.get("/auth/me", headers=session["headers"])
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"
