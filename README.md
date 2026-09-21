# OsonIjara Backend

FastAPI + PostgreSQL backend for the OsonIjara Flutter app — JWT auth, property
listings with filters, image uploads (avatars + property photos), and
bookmarks, all Dockerized.

## Stack (and why)
- **FastAPI** — fast to build, async-ready, and gives you interactive docs
  (`/docs`) for free alongside the Postman collection.
- **PostgreSQL** — solid relational fit for users/properties/images/bookmarks.
- **SQLAlchemy 2.0** — ORM; tables are auto-created on startup for this MVP
  (swap in Alembic migrations once the schema needs to evolve safely).
- **JWT (python-jose) + passlib/bcrypt** — stateless auth, hashed passwords.
- **Docker Compose** — spins up the API, Postgres, and Adminer (a lightweight
  DB browser) together.

## Run it

```bash
cd oson_ijara_backend
cp backend/.env.example backend/.env   # already done for you, but review it
docker compose up --build
```

- API: http://localhost:8000 (interactive docs at http://localhost:8000/docs)
- Postgres: localhost:5433 (user `oson`, password `oson_secret`, db `oson_ijara`)
- Adminer (DB browser): http://localhost:8080 — system: PostgreSQL, server: `db`,
  user: `oson`, password: `oson_secret`, database: `oson_ijara`

Uploaded files land in `backend/uploads/` on your host machine (mounted as a
volume), and are served back at `http://localhost:8000/uploads/...`.

## Testing with Postman
Import `postman/OsonIjara_API.postman_collection.json` into Postman. It's set
up with:
- A `base_url` collection variable (`http://localhost:8000`)
- `Register` / `Login` requests that **automatically save the JWT** into a
  `token` variable via a test script, so every other request's Bearer auth
  just works after you run one of them once.
- A `property_id` variable that auto-fills after "Create property", so the
  update/upload-images/save/delete requests target the listing you just made.

Suggested run order: **Register → Create property → Upload property images →
List properties → Toggle save / bookmark → My saved listings**.

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /auth/register | – | Create account, returns JWT |
| POST | /auth/login | – | OAuth2 form login (`username` = email), returns JWT |
| GET | /auth/me | ✓ | Current user |
| PUT | /users/me | ✓ | Update name/email/phone/password |
| POST | /users/me/avatar | ✓ | Upload profile picture (`file`) |
| GET | /users/me/saved | ✓ | List bookmarked properties |
| GET | /properties | – | List + filter (location, price range, min bedrooms/bathrooms, renovation, amenities, student_only, search) |
| GET | /properties/{id} | – | Property detail |
| POST | /properties | ✓ | Create a listing |
| PUT | /properties/{id} | ✓ (owner) | Update a listing |
| DELETE | /properties/{id} | ✓ (owner) | Delete a listing |
| POST | /properties/{id}/images | ✓ (owner) | Upload one or more photos (`files`) |
| DELETE | /properties/{id}/images/{image_id} | ✓ (owner) | Remove one photo |
| POST | /properties/{id}/save | ✓ | Toggle bookmark |

## Next steps
- Add Alembic migrations once you need to change the schema without wiping data.
- Swap the CORS wildcard and the sample `SECRET_KEY` before this ever handles
  data you care about.

## Deploying it live (free)

This uses **Neon** for a permanent free Postgres database (Render's own free
Postgres expires after 30 days, which doesn't fit "keep this live indefinitely
for a portfolio") and **Render** for the API itself.

**Known limitation, by design of the free tier:** Render's free web service
spins down after 15 minutes idle and has no persistent disk on that tier — so
uploaded photos won't survive a restart. Everything else (accounts, listings,
bookmarks — anything in Postgres) persists fine. A production version would
swap local file storage for something like Cloudflare R2 or S3.

### 1. Create the database on Neon
1. Sign up at [neon.tech](https://neon.tech) (no card required).
2. Create a project — any name, any region.
3. Copy the connection string it gives you (starts with `postgresql://`).
   Keep it handy for the next step.

### 2. Deploy the API on Render
1. Push this `oson_ijara_backend` folder to its own GitHub repo.
2. Sign up at [render.com](https://render.com) and click **New > Web Service**.
3. Connect that GitHub repo. Set:
   - **Root Directory**: `backend`
   - **Environment**: Docker (Render will find the `Dockerfile` automatically)
4. Under **Environment Variables**, add:
   - `DATABASE_URL` → the Neon connection string from step 1
   - `SECRET_KEY` → any long random string (e.g. generate one with
     `python -c "import secrets; print(secrets.token_hex(32))"`)
   - `ALGORITHM` → `HS256`
   - `ACCESS_TOKEN_EXPIRE_MINUTES` → `1440`
   - `UPLOAD_DIR` → `uploads`
5. Deploy. Render gives you a URL like `https://oson-ijara-backend.onrender.com`.
6. Visit `<that-url>/docs` — if the Swagger UI loads, it's alive and connected.

That's it for the backend — tables are created automatically on first startup,
same as locally.

### 3. Update the Postman collection (optional, for re-testing against the live API)
Change the collection's `base_url` variable from `http://localhost:8000` to
your Render URL, and re-run the same request sequence as before.
