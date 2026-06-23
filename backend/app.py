import os
import random
import string
from datetime import datetime

import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, redirect, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ── Config ────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL")
BASE_URL      = os.getenv("BASE_URL", "http://localhost")
SHORT_CODE_LENGTH = 6


# ── Database ───────────────────────────────────────────────────
def get_db():
    """Open a new database connection."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def init_db():
    """Create the urls table if it doesn't exist."""
    sql = """
        CREATE TABLE IF NOT EXISTS urls (
            id          SERIAL PRIMARY KEY,
            short_code  VARCHAR(20)  NOT NULL UNIQUE,
            original_url TEXT        NOT NULL,
            created_at  TIMESTAMP    NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_short_code ON urls (short_code);
    """
    conn = get_db()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql)
    finally:
        conn.close()


# ── Helpers ────────────────────────────────────────────────────
def generate_short_code(length=SHORT_CODE_LENGTH):
    """Return a random alphanumeric string."""
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


def is_valid_url(url: str) -> bool:
    """Basic validation — must start with http:// or https://."""
    return url.startswith("http://") or url.startswith("https://")


# ── Routes ─────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint used by Docker and load balancers."""
    return jsonify({"status": "ok"}), 200


@app.route("/shorten", methods=["POST"])
def shorten():
    """
    Accept a long URL, store it with a unique short code, and return the short URL.

    Request body (JSON):
        { "url": "https://example.com/very/long/path" }

    Response (JSON):
        { "short_url": "http://localhost/abc123" }
    """
    data = request.get_json(silent=True)

    # ── Validate input ─────────────────────────────
    if not data or "url" not in data:
        return jsonify({"error": "Request body must be JSON with a 'url' field."}), 400

    original_url = data["url"].strip()

    if not original_url:
        return jsonify({"error": "URL cannot be empty."}), 400

    if not is_valid_url(original_url):
        return jsonify({"error": "URL must start with http:// or https://"}), 422

    if len(original_url) > 2048:
        return jsonify({"error": "URL is too long (max 2048 characters)."}), 422

    # ── Store in database ──────────────────────────
    conn = get_db()
    try:
        with conn:
            with conn.cursor() as cur:

                # Re-use existing short code if this URL was already shortened
                cur.execute(
                    "SELECT short_code FROM urls WHERE original_url = %s LIMIT 1;",
                    (original_url,)
                )
                row = cur.fetchone()

                if row:
                    short_code = row["short_code"]
                else:
                    # Generate a unique short code (retry on collision)
                    for _ in range(5):
                        candidate = generate_short_code()
                        cur.execute(
                            "SELECT 1 FROM urls WHERE short_code = %s;",
                            (candidate,)
                        )
                        if not cur.fetchone():
                            short_code = candidate
                            break
                    else:
                        return jsonify({"error": "Could not generate a unique code. Try again."}), 500

                    cur.execute(
                        "INSERT INTO urls (short_code, original_url) VALUES (%s, %s);",
                        (short_code, original_url)
                    )

    except psycopg2.Error as e:
        app.logger.error("Database error in /shorten: %s", e)
        return jsonify({"error": "Database error. Please try again."}), 500
    finally:
        conn.close()

    short_url = f"{BASE_URL.rstrip('/')}/{short_code}"
    return jsonify({"short_url": short_url}), 201


@app.route("/<short_code>", methods=["GET"])
def redirect_to_original(short_code):
    """
    Look up the short code and redirect to the original URL.
    Returns 404 if the code doesn't exist.
    """
    # Basic sanity check on the short code format
    if not short_code.isalnum() or len(short_code) > 20:
        return jsonify({"error": "Invalid short code."}), 404

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT original_url FROM urls WHERE short_code = %s LIMIT 1;",
                (short_code,)
            )
            row = cur.fetchone()
    except psycopg2.Error as e:
        app.logger.error("Database error in redirect: %s", e)
        return jsonify({"error": "Database error."}), 500
    finally:
        conn.close()

    if not row:
        return jsonify({"error": f"Short code '{short_code}' not found."}), 404

    return redirect(row["original_url"], code=302)

# Ensure the table exists whether run directly or via Gunicorn
init_db()

# ── Startup ────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)
