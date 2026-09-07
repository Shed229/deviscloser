import os
import re
import secrets
import hashlib
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import quote

import psycopg2
from psycopg2.extras import RealDictCursor
from flask import (
    Flask, request, redirect, session, url_for,
    render_template_string, flash, abort, Response
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


# ============================================================
# DEVIS CLOSER
# Transformez vos devis en contrats.
# Application monolithique Flask + PostgreSQL
# ============================================================

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "CHANGE-ME-IN-RENDER"
)

app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("RENDER", "").lower() == "true",
)


# ============================================================
# CONFIGURATION
# ============================================================

APP_NAME = os.environ.get("APP_NAME", "Devis Closer")
APP_SLOGAN = os.environ.get(
    "APP_SLOGAN",
    "Transformez vos devis en contrats"
)

COMMISSION_RATE = Decimal(
    os.environ.get("COMMISSION_RATE", "0.02")
)

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

MOMO_NUMBER = os.environ.get("MOMO_NUMBER", "")
MOMO_NUMBER_INT = os.environ.get("MOMO_NUMBER_INT", "")
MOMO_NAME = os.environ.get("MOMO_NAME", "")

BSC_ADDRESS = os.environ.get("BSC_ADDRESS", "")
TRON_ADDRESS = os.environ.get("TRON_ADDRESS", "")

DATABASE_URL = os.environ.get("DATABASE_URL", "")

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

COUNTRIES = [
    ("BJ", "Bénin", "XOF"),
    ("CI", "Côte d'Ivoire", "XOF"),
    ("TG", "Togo", "XOF"),
    ("SN", "Sénégal", "XOF"),
    ("CM", "Cameroun", "XAF"),
    ("FR", "France", "EUR"),
    ("BE", "Belgique", "EUR"),
    ("CA", "Canada", "CAD"),
    ("US", "États-Unis", "USD"),
    ("GB", "Royaume-Uni", "GBP"),
    ("ES", "Espagne", "EUR"),
    ("PT", "Portugal", "EUR"),
    ("DE", "Allemagne", "EUR"),
    ("IT", "Italie", "EUR"),
    ("CH", "Suisse", "CHF"),
    ("MA", "Maroc", "MAD"),
    ("NG", "Nigeria", "NGN"),
    ("GH", "Ghana", "GHS"),
    ("ZA", "Afrique du Sud", "ZAR"),
    ("IN", "Inde", "INR"),
    ("AE", "Émirats arabes unis", "AED"),
    ("AU", "Australie", "AUD"),
    ("BR", "Brésil", "BRL"),
]

PLANS = {
    "free": {
        "name": "Free",
        "price": Decimal("0"),
        "quotes": 1,
        "clients": 5,
        "users": 1,
        "features": [
            "1 devis par mois",
            "5 clients",
            "WhatsApp",
            "Email",
            "Lien public",
            "Suivi basique",
            "1 modèle",
            "Tableau de bord basique",
        ],
    },
    "starter": {
        "name": "Starter",
        "price": Decimal("6500"),
        "quotes": 50,
        "clients": 100,
        "users": 2,
        "features": [
            "50 devis par mois",
            "100 clients",
            "WhatsApp + email",
            "Suivi des devis",
            "Relances",
            "5 modèles",
            "Signature électronique",
            "Paiement des devis",
            "Statistiques",
            "Historique client",
            "2 utilisateurs",
        ],
    },
    "pro": {
        "name": "Pro",
        "price": Decimal("15000"),
        "quotes": None,
        "clients": None,
        "users": 5,
        "features": [
            "Devis illimités",
            "Clients illimités",
            "Relances automatiques",
            "Modèles illimités",
            "Signature électronique",
            "Paiement des devis",
            "Statistiques avancées",
            "Historique complet",
            "AI Closer",
            "Détection des prospects chauds",
            "Suggestions de relance",
            "Assistance à la négociation",
            "5 utilisateurs",
            "Support prioritaire",
        ],
    },
}


# ============================================================
# BASE DE DONNÉES
# ============================================================

def db():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL n'est pas configurée dans Render."
        )

    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor,
        sslmode="require"
    )


def query(sql, params=(), fetch=False, one=False):
    conn = db()

    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)

            if fetch:
                result = cur.fetchone() if one else cur.fetchall()
            else:
                result = None

        conn.commit()
        return result

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def init_db():
    conn = db()

    try:
        with conn.cursor() as cur:

            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name VARCHAR(255) NOT NULL,
                    company_name VARCHAR(255),
                    phone VARCHAR(100),
                    address TEXT,
                    country VARCHAR(100),
                    currency VARCHAR(20) DEFAULT 'XOF',
                    language VARCHAR(20) DEFAULT 'fr',
                    timezone VARCHAR(100) DEFAULT 'Africa/Porto-Novo',
                    role VARCHAR(30) DEFAULT 'user',
                    cgu_version VARCHAR(30),
                    cgu_accepted_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    active BOOLEAN DEFAULT TRUE
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id)
                        ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    company VARCHAR(255),
                    email VARCHAR(255),
                    phone VARCHAR(100),
                    address TEXT,
                    country VARCHAR(100),
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS quotes (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id)
                        ON DELETE CASCADE,
                    customer_id INTEGER REFERENCES customers(id)
                        ON DELETE SET NULL,
                    quote_number VARCHAR(100) NOT NULL,
                    title VARCHAR(255),
                    description TEXT,
                    amount NUMERIC(14,2) NOT NULL DEFAULT 0,
                    tax NUMERIC(14,2) NOT NULL DEFAULT 0,
                    discount NUMERIC(14,2) NOT NULL DEFAULT 0,
                    total NUMERIC(14,2) NOT NULL DEFAULT 0,
                    currency VARCHAR(20) DEFAULT 'XOF',
                    status VARCHAR(30) DEFAULT 'draft',
                    public_token VARCHAR(150) UNIQUE NOT NULL,
                    expires_at DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS quote_events (
                    id SERIAL PRIMARY KEY,
                    quote_id INTEGER NOT NULL REFERENCES quotes(id)
                        ON DELETE CASCADE,
                    event_type VARCHAR(50) NOT NULL,
                    description TEXT,
                    ip_address VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS signatures (
                    id SERIAL PRIMARY KEY,
                    quote_id INTEGER NOT NULL REFERENCES quotes(id)
                        ON DELETE CASCADE,
                    signer_name VARCHAR(255) NOT NULL,
                    signer_email VARCHAR(255),
                    ip_address VARCHAR(100),
                    signed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id)
                        ON DELETE CASCADE,
                    plan VARCHAR(30) NOT NULL DEFAULT 'free',
                    status VARCHAR(30) DEFAULT 'active',
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS subscription_payments (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id)
                        ON DELETE CASCADE,
                    plan VARCHAR(30) NOT NULL,
                    amount NUMERIC(14,2) NOT NULL,
                    currency VARCHAR(20) DEFAULT 'XOF',
                    payment_method VARCHAR(50) NOT NULL,
                    transaction_id VARCHAR(255) UNIQUE,
                    proof_data BYTEA,
                    proof_mime VARCHAR(100),
                    proof_filename VARCHAR(255),
                    status VARCHAR(30) DEFAULT 'pending',
                    rejection_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    verified_at TIMESTAMP,
                    verified_by INTEGER REFERENCES users(id)
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS quote_payments (
                    id SERIAL PRIMARY KEY,
                    quote_id INTEGER NOT NULL REFERENCES quotes(id)
                        ON DELETE CASCADE,
                    professional_id INTEGER NOT NULL REFERENCES users(id)
                        ON DELETE CASCADE,
                    amount NUMERIC(14,2) NOT NULL,
                    commission NUMERIC(14,2) NOT NULL,
                    net_amount NUMERIC(14,2) NOT NULL,
                    currency VARCHAR(20) DEFAULT 'XOF',
                    payment_method VARCHAR(50) NOT NULL,
                    transaction_id VARCHAR(255) UNIQUE,
                    proof_data BYTEA,
                    proof_mime VARCHAR(100),
                    proof_filename VARCHAR(255),
                    status VARCHAR(30) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    verified_at TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id)
                        ON DELETE CASCADE,
                    title VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id SERIAL PRIMARY KEY,
                    admin_id INTEGER REFERENCES users(id),
                    action VARCHAR(255) NOT NULL,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_customers_user
                ON customers(user_id)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_quotes_user
                ON quotes(user_id)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_quote_events_quote
                ON quote_events(quote_id)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_payments_status
                ON subscription_payments(status)
            """)

            # Création automatique du compte administrateur.
            if ADMIN_EMAIL and ADMIN_PASSWORD:
                cur.execute(
                    "SELECT id FROM users WHERE email=%s",
                    (ADMIN_EMAIL,)
                )

                admin = cur.fetchone()

                if not admin:
                    cur.execute("""
                        INSERT INTO users (
                            email,
                            password_hash,
                            full_name,
                            role,
                            cgu_version,
                            cgu_accepted_at
                        )
                        VALUES (%s,%s,%s,'admin','1.0',CURRENT_TIMESTAMP)
                    """, (
                        ADMIN_EMAIL,
                        generate_password_hash(ADMIN_PASSWORD),
                        "Administrateur Devis Closer"
                    ))
                else:
                    cur.execute("""
                        UPDATE users
                        SET role='admin',
                            active=TRUE
                        WHERE email=%s
                    """, (ADMIN_EMAIL,))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# ============================================================
# SÉCURITÉ
# ============================================================

def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def validate_csrf():
    if request.method != "POST":
        return

    sent = request.form.get("csrf_token", "")

    if not sent or sent != session.get("csrf"):
        abort(400, "Requête invalide.")


@app.before_request
def before_request():
    if request.method == "POST":
        validate_csrf()


@app.context_processor
def inject_globals():
    return {
        "csrf_token": csrf_token(),
        "app_name": APP_NAME,
        "app_slogan": APP_SLOGAN,
    }


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Connectez-vous pour continuer.", "warning")
            return redirect(url_for("connexion"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("connexion"))

        user = query(
            "SELECT * FROM users WHERE id=%s",
            (session["user_id"],),
            fetch=True,
            one=True
        )

        if not user or user["role"] != "admin":
            abort(403)

        return view(*args, **kwargs)

    return wrapped


def current_user():
    uid = session.get("user_id")

    if not uid:
        return None

    return query(
        "SELECT * FROM users WHERE id=%s AND active=TRUE",
        (uid,),
        fetch=True,
        one=True
    )


# ============================================================
# UTILITAIRES
# ============================================================

def money(value):
    try:
        return f"{Decimal(str(value)):,.2f}"
    except Exception:
        return "0.00"


def parse_decimal(value):
    try:
        value = str(value).replace(" ", "").replace(",", ".")
        return Decimal(value or "0")
    except InvalidOperation:
        return Decimal("0")


def allowed_image(filename):
    if not filename or "." not in filename:
        return False

    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_IMAGE_EXTENSIONS


def get_quote_for_owner(quote_id, user_id):
    return query("""
        SELECT q.*, c.name AS customer_name,
               c.email AS customer_email,
               c.phone AS customer_phone
        FROM quotes q
        LEFT JOIN customers c ON c.id=q.customer_id
        WHERE q.id=%s AND q.user_id=%s
    """, (quote_id, user_id), fetch=True, one=True)


def add_quote_event(quote_id, event_type, description=""):
    query("""
        INSERT INTO quote_events
        (quote_id,event_type,description,ip_address)
        VALUES (%s,%s,%s,%s)
    """, (
        quote_id,
        event_type,
        description,
        request.remote_addr
    ))


def create_notification(user_id, title, message):
    query("""
        INSERT INTO notifications(user_id,title,message)
        VALUES (%s,%s,%s)
    """, (user_id, title, message))


def subscription_for(user_id):
    return query("""
        SELECT *
        FROM subscriptions
        WHERE user_id=%s
        ORDER BY id DESC
        LIMIT 1
    """, (user_id,), fetch=True, one=True)


def plan_for(user_id):
    sub = subscription_for(user_id)

    if not sub:
        return "free"

    if sub["status"] != "active":
        return "free"

    if sub["expires_at"] and sub["expires_at"] < datetime.utcnow():
        return "free"

    return sub["plan"]


def check_plan_limit(user_id, kind):
    plan_name = plan_for(user_id)
    plan = PLANS.get(plan_name, PLANS["free"])

    if kind == "quotes":
        limit = plan["quotes"]

        if limit is None:
            return True

        row = query("""
            SELECT COUNT(*) AS count
            FROM quotes
            WHERE user_id=%s
            AND created_at >= date_trunc('month', CURRENT_TIMESTAMP)
        """, (user_id,), fetch=True, one=True)

    else:
        limit = plan["clients"]

        if limit is None:
            return True

        row = query("""
            SELECT COUNT(*) AS count
            FROM customers
            WHERE user_id=%s
        """, (user_id,), fetch=True, one=True)

    return int(row["count"]) < limit


def quote_status_label(status):
    return {
        "draft": "Brouillon",
        "sent": "Envoyé",
        "viewed": "Consulté",
        "negotiation": "Négociation",
        "accepted": "Accepté",
        "signed": "Signé",
        "paid": "Payé",
        "refused": "Refusé",
        "expired": "Expiré",
    }.get(status, status)


# ============================================================
# DESIGN
# ============================================================

BASE = """
<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport"
      content="width=device-width, initial-scale=1">
<meta name="description"
      content="Devis Closer — Transformez vos devis en contrats.">
<title>{{ title or app_name }}</title>

<style>
*{box-sizing:border-box}
body{
    margin:0;
    font-family:Inter,Arial,sans-serif;
    background:#070b14;
    color:#f5f7fb;
}
a{text-decoration:none;color:inherit}
nav{
    display:flex;
    align-items:center;
    justify-content:space-between;
    padding:18px 5%;
    border-bottom:1px solid #1c2637;
    background:#080d18;
    position:sticky;
    top:0;
    z-index:20;
}
.logo{
    font-weight:900;
    font-size:21px;
}
.logo span{color:#4da3ff}
.navlinks{
    display:flex;
    gap:15px;
    align-items:center;
    flex-wrap:wrap;
}
.navlinks a{
    color:#b7c1d1;
    font-size:14px;
}
.container{
    width:min(1150px,92%);
    margin:35px auto;
}
.hero{
    padding:65px 20px;
    text-align:center;
}
.hero h1{
    font-size:clamp(38px,7vw,72px);
    margin:10px 0;
}
.hero p{
    color:#aeb9ca;
    f
