# URL Shortener

A full-stack, containerized URL shortener built as a hands-on DevOps learning project. It covers a complete application stack — frontend, backend, database, reverse proxy, containerization, and CI/CD — deployed on AWS EC2.

**Live demo:** `http://<your-ec2-public-ip>`

---

## Features

- Shorten any long URL into a compact link
- Idempotent shortening — submitting the same URL twice returns the same short code
- Redirect from short code to the original URL
- Copy-to-clipboard for generated short links
- Health check endpoint for container orchestration

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML / CSS / Vanilla JavaScript |
| Backend | Flask (Python) + Gunicorn |
| Database | PostgreSQL |
| Reverse Proxy | Nginx |
| Containerization | Docker Compose |
| CI/CD | GitHub Actions |
| Deployment | AWS EC2 (Ubuntu) |

---

## Architecture

```
Browser
   │
   ▼
 Nginx (port 80)
   ├── / ──────────► serves frontend/index.html (static)
   ├── /shorten ────► proxies to Flask
   ├── /health ─────► proxies to Flask
   └── /<code> ─────► proxies to Flask (redirect)
                          │
                          ▼
                    Flask backend (port 5000)
                          │
                          ▼
                    PostgreSQL (port 5432)
```

All three services run in isolated Docker containers, networked together via Docker Compose. Only Nginx is exposed to the host — the database and backend are reachable only on the internal Docker network.

---

## Project Structure

```
url-shortener/
├── frontend/
│   └── index.html          # UI with form, result display, copy button
├── backend/
│   ├── app.py               # Flask API (/shorten, /<code>, /health)
│   ├── requirements.txt
│   └── Dockerfile           # Multi-stage build, non-root user, Gunicorn
├── nginx/
│   └── nginx.conf           # Reverse proxy + static file serving
├── .github/
│   └── workflows/
│       └── deploy.yml       # CI/CD: test → build/push → deploy
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/shorten` | Accepts `{ "url": "..." }`, returns `{ "short_url": "..." }` |
| `GET` | `/<short_code>` | Redirects (302) to the original URL |
| `GET` | `/health` | Returns `{ "status": "ok" }` |

**Example:**
```bash
curl -X POST http://localhost/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```
```json
{ "short_url": "http://localhost/aB3xQ9" }
```

---

## Running Locally

> Requires Docker and Docker Compose installed and running.

**1. Clone the repository:**
```bash
git clone https://github.com/MAACAH/url-shortener.git
cd url-shortener
```

**2. Create your `.env` file:**
```bash
cp .env.example .env
```
Edit `.env` and set a real password — make sure `POSTGRES_PASSWORD` matches the password used in `DATABASE_URL`.

**3. Build and start all services:**
```bash
docker compose up --build
```

**4. Open the app:**
```
http://localhost
```

**5. Stop everything:**
```bash
docker compose down
```

---

## Environment Variables

Set in `.env` (never committed — see `.env.example` for the template):

| Variable | Description |
|---|---|
| `POSTGRES_DB` | Database name |
| `POSTGRES_USER` | Database user |
| `POSTGRES_PASSWORD` | Database password |
| `DATABASE_URL` | Full Postgres connection string used by Flask |
| `BASE_URL` | Public base URL used to build short links |

---

## Deployment (AWS EC2)

1. Launch an Ubuntu EC2 instance (free tier `t2.micro` works)
2. Open inbound ports `22` (SSH) and `80` (HTTP) in the security group
3. SSH into the instance and install Docker:
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   ```
4. Clone the repo and add a `.env` file on the server
5. Run:
   ```bash
   docker compose up --build -d
   ```
6. Visit the app at `http://<ec2-public-ip>`

---

## CI/CD Pipeline

`.github/workflows/deploy.yml` runs on every push to `main`:

1. **Test** — spins up a Postgres service container, installs dependencies, verifies the app initializes correctly
2. **Build & Push** — builds the backend Docker image and pushes it to Docker Hub, tagged with the commit SHA and `latest`
3. **Deploy** — SSHs into the EC2 server, pulls the latest code/images, and restarts the stack

**Required GitHub Secrets:**

| Secret | Purpose |
|---|---|
| `DOCKER_USERNAME` / `DOCKER_PASSWORD` | Docker Hub login |
| `SERVER_HOST` | EC2 public IP |
| `SERVER_USER` | SSH username (`ubuntu`) |
| `SERVER_SSH_KEY` | Private SSH key for deployment |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | Database credentials |
| `DATABASE_URL` | Full DB connection string |
| `BASE_URL` | Public base URL for short links |

> **Status:** Pipeline file is written but not yet wired up with secrets — manual deployment is currently used. See [Roadmap](#roadmap).

---

## Troubleshooting Notes

A few real issues hit during development, kept here for reference:

- **`relation "urls" does not exist`** — Gunicorn imports `app.py` as a module rather than running it as `__main__`, so `init_db()` must be called at module level, not only inside `if __name__ == "__main__":`.
- **`password authentication failed`** — Postgres only applies `.env` credentials the *first* time its data volume is created. If you change `.env` afterward, reset with `docker compose down -v` to reinitialize.
- **`pcre2_compile() failed` in Nginx** — a malformed regex in a `location` block. Keeping the config free of complex regex (using `try_files` + a named `@backend` location instead) avoids this entirely.

---

## Roadmap

- [ ] Wire up GitHub Actions secrets for automatic deployment
- [ ] Re-add Nginx security headers (`X-Frame-Options`, `X-Content-Type-Options`, etc.)
- [ ] Add an Elastic IP so the EC2 address doesn't change on restart
- [ ] Add click tracking / visit counter per short link
- [ ] Add link expiry
- [ ] Add custom alias support (user-chosen short codes)
- [ ] Add automated tests for the Flask API

---

## License

This project is open source and available for learning purposes.
