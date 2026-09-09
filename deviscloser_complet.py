import os
import re
import threading
import secrets
import hashlib
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime, timedelta, timezone
from functools import wraps
from io import BytesIO

import psycopg2
from psycopg2 import pool
from flask import Flask, request, redirect, url_for, session, render_template_string, flash, abort, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ============================================================
# DEVIS CLOSER — Transformez vos devis en contrats
# Monofichier Flask + PostgreSQL — Python 3.11
# Dépendances: Flask, Werkzeug, psycopg2-binary, gunicorn
# ============================================================

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "change-me-in-render"),
    MAX_CONTENT_LENGTH=2 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("RENDER", "").lower() == "true",
)

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL est obligatoire sur Render.")

# Pour les environnements Render, postgres:// peut encore apparaître.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

DB_POOL = None
DB_READY = False
ADMIN_READY = False
DB_LOCK = threading.Lock()

OWNER_NAME = os.environ.get("MOMO_NAME", "Sosthene Herve EDOH")
OWNER_MOMO = os.environ.get("MOMO", "01 56 85 31 49")
OWNER_MOMO_INT = os.environ.get("MOMO_INT", "2290156853149")
OWNER_BSC = os.environ.get("BSC_ADDR", "")
OWNER_TRON = os.environ.get("TRON_ADDR", "")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
CGU_VERSION = "1.0"

PLANS = {
    "free": {
        "name": "Free", "price": Decimal("0"), "quotes": 5, "clients": 5, "users": 1,
        "features": ["5 devis/mois", "5 clients", "WhatsApp", "Email", "Lien public", "Suivi de base", "1 modèle", "Dashboard de base"]
    },
    "starter": {
        "name": "Starter", "price": Decimal("6500"), "quotes": 30, "clients": 100, "users": 2,
        "features": ["30 devis/mois", "100 clients", "WhatsApp + email", "Suivi des devis", "Relances", "5 modèles", "Signature électronique", "Paiements de devis", "Statistiques", "Historique client", "2 utilisateurs"]
    },
    "pro": {
        "name": "Pro", "price": Decimal("15000"), "quotes": None, "clients": None, "users": 5,
        "features": ["Devis illimités", "Clients illimités", "Relances automatiques", "Modèles illimités", "Signature électronique", "Paiements de devis", "Statistiques avancées", "Historique complet", "AI Closer", "Prospects chauds", "Aide à la négociation", "5 utilisateurs", "Support prioritaire"]
    },
}

COUNTRIES = [
    ("BJ", "Bénin"), ("TG", "Togo"), ("CI", "Côte d’Ivoire"), ("GH", "Ghana"), ("NG", "Nigeria"),
    ("SN", "Sénégal"), ("BF", "Burkina Faso"), ("NE", "Niger"), ("ML", "Mali"), ("GN", "Guinée"),
    ("CM", "Cameroun"), ("CD", "République démocratique du Congo"), ("CG", "Congo"), ("GA", "Gabon"),
    ("MA", "Maroc"), ("DZ", "Algérie"), ("TN", "Tunisie"), ("FR", "France"), ("BE", "Belgique"),
    ("CH", "Suisse"), ("CA", "Canada"), ("US", "États-Unis"), ("GB", "Royaume-Uni"), ("DE", "Allemagne"),
    ("ES", "Espagne"), ("IT", "Italie"), ("PT", "Portugal"), ("NL", "Pays-Bas"), ("BR", "Brésil"),
    ("IN", "Inde"), ("CN", "Chine"), ("JP", "Japon"), ("AU", "Australie"), ("AE", "Émirats arabes unis"),
    ("ZA", "Afrique du Sud"), ("KE", "Kenya"), ("RW", "Rwanda"), ("TZ", "Tanzanie"), ("UG", "Ouganda"),
    ("ET", "Éthiopie"), ("EG", "Égypte"), ("SA", "Arabie saoudite"), ("TR", "Turquie"), ("MX", "Mexique"),
]

CURRENCIES = ["XOF", "XAF", "USD", "EUR", "GBP", "CAD", "CHF", "NGN", "GHS", "MAD", "DZD", "BRL", "INR", "CNY", "JPY", "AUD", "AED", "ZAR"]

# ----------------------------
# DB
# ----------------------------

def db_init():
    global DB_POOL, DB_READY
    if DB_READY and DB_POOL is not None:
        return
    with DB_LOCK:
        if DB_READY and DB_POOL is not None:
            return
        if DB_POOL is None:
            DB_POOL = pool.SimpleConnectionPool(1, 5, dsn=DATABASE_URL, connect_timeout=10)
    conn = DB_POOL.getconn()
    try:
        conn.autocommit = True
        cur = conn.cursor()
        statements = [
            """CREATE TABLE IF NOT EXISTS users (
                id BIGSERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                company_name TEXT,
                phone TEXT,
                address TEXT,
                country TEXT,
                currency TEXT DEFAULT 'XOF',
                language TEXT DEFAULT 'fr',
                timezone TEXT DEFAULT 'Africa/Porto-Novo',
                role TEXT DEFAULT 'user',
                cgu_accepted BOOLEAN DEFAULT FALSE,
                cgu_version TEXT,
                cgu_accepted_at TIMESTAMP,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS customers (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                company TEXT,
                email TEXT,
                phone TEXT,
                address TEXT,
                country TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS quotes (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                customer_id BIGINT REFERENCES customers(id) ON DELETE SET NULL,
                quote_number TEXT NOT NULL,
                public_token TEXT UNIQUE NOT NULL,
                description TEXT,
                currency TEXT DEFAULT 'XOF',
                subtotal NUMERIC(14,2) DEFAULT 0,
                discount NUMERIC(14,2) DEFAULT 0,
                tax NUMERIC(14,2) DEFAULT 0,
                total NUMERIC(14,2) DEFAULT 0,
                terms TEXT,
                status TEXT DEFAULT 'draft',
                issue_date DATE DEFAULT CURRENT_DATE,
                expires_at DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS quote_items (
                id BIGSERIAL PRIMARY KEY,
                quote_id BIGINT NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
                description TEXT NOT NULL,
                quantity NUMERIC(12,2) DEFAULT 1,
                unit_price NUMERIC(14,2) DEFAULT 0,
                line_total NUMERIC(14,2) DEFAULT 0
            )""",
            """CREATE TABLE IF NOT EXISTS quote_events (
                id BIGSERIAL PRIMARY KEY,
                quote_id BIGINT NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
                event_type TEXT NOT NULL,
                message TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS signatures (
                id BIGSERIAL PRIMARY KEY,
                quote_id BIGINT NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
                signer_name TEXT NOT NULL,
                signer_email TEXT,
                signature_text TEXT NOT NULL,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS payment_settings (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                momo_operator TEXT,
                momo_number TEXT,
                momo_name TEXT,
                usdt_trc20 TEXT,
                usdt_bep20 TEXT,
                bnb_address TEXT,
                tron_address TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS subscriptions (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                plan TEXT NOT NULL DEFAULT 'free',
                status TEXT NOT NULL DEFAULT 'active',
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                payment_id BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS subscription_payments (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                plan TEXT NOT NULL,
                amount NUMERIC(14,2) NOT NULL,
                currency TEXT DEFAULT 'XOF',
                payment_method TEXT NOT NULL,
                transaction_id TEXT UNIQUE,
                proof_data BYTEA,
                proof_mime TEXT,
                proof_filename TEXT,
                status TEXT DEFAULT 'pending',
                rejection_reason TEXT,
                verified_by BIGINT REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_at TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS quote_payments (
                id BIGSERIAL PRIMARY KEY,
                quote_id BIGINT NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
                professional_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                gross_amount NUMERIC(14,2) NOT NULL,
                commission_amount NUMERIC(14,2) NOT NULL,
                net_amount NUMERIC(14,2) NOT NULL,
                currency TEXT DEFAULT 'XOF',
                payment_method TEXT NOT NULL,
                transaction_id TEXT UNIQUE,
                proof_data BYTEA,
                proof_mime TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_at TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS notifications (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS admin_logs (
                id BIGSERIAL PRIMARY KEY,
                admin_id BIGINT REFERENCES users(id),
                action TEXT NOT NULL,
                target_type TEXT,
                target_id BIGINT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
        ]
        for sql in statements:
            cur.execute(sql)

        migrations = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS company_name TEXT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone TEXT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS address TEXT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS country TEXT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS currency TEXT DEFAULT 'XOF'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS language TEXT DEFAULT 'fr'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'Africa/Porto-Novo'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'user'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS cgu_accepted BOOLEAN DEFAULT FALSE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS cgu_version TEXT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS cgu_accepted_at TIMESTAMP",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT TRUE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "ALTER TABLE quotes ADD COLUMN IF NOT EXISTS description TEXT",
            "ALTER TABLE quotes ADD COLUMN IF NOT EXISTS currency TEXT DEFAULT 'XOF'",
            "ALTER TABLE quotes ADD COLUMN IF NOT EXISTS subtotal NUMERIC(14,2) DEFAULT 0",
            "ALTER TABLE quotes ADD COLUMN IF NOT EXISTS discount NUMERIC(14,2) DEFAULT 0",
            "ALTER TABLE quotes ADD COLUMN IF NOT EXISTS tax NUMERIC(14,2) DEFAULT 0",
            "ALTER TABLE quotes ADD COLUMN IF NOT EXISTS total NUMERIC(14,2) DEFAULT 0",
            "ALTER TABLE quotes ADD COLUMN IF NOT EXISTS terms TEXT",
            "ALTER TABLE quotes ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'draft'",
            "ALTER TABLE quotes ADD COLUMN IF NOT EXISTS issue_date DATE DEFAULT CURRENT_DATE",
            "ALTER TABLE quotes ADD COLUMN IF NOT EXISTS expires_at DATE",
            "ALTER TABLE quotes ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "ALTER TABLE quotes ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS payment_id BIGINT",
            "ALTER TABLE subscription_payments ADD COLUMN IF NOT EXISTS rejection_reason TEXT",
            "ALTER TABLE subscription_payments ADD COLUMN IF NOT EXISTS verified_by BIGINT REFERENCES users(id)",
            "ALTER TABLE subscription_payments ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP",
            "ALTER TABLE quote_payments ADD COLUMN IF NOT EXISTS proof_data BYTEA",
            "ALTER TABLE quote_payments ADD COLUMN IF NOT EXISTS proof_mime TEXT",
            "ALTER TABLE quote_payments ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending'",
            "ALTER TABLE quote_payments ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP",
            "CREATE TABLE IF NOT EXISTS password_resets (id BIGSERIAL PRIMARY KEY,user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,token_hash TEXT UNIQUE,expires_at TIMESTAMP,used BOOLEAN DEFAULT FALSE)",
        ]
        for sql in migrations:
            cur.execute(sql)

        # Les index sont créés après les migrations afin de rester compatibles
        # avec une base créée par une ancienne version.
        for sql in [
            "CREATE INDEX IF NOT EXISTS idx_quotes_user ON quotes(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_quotes_status ON quotes(status)",
            "CREATE INDEX IF NOT EXISTS idx_events_quote ON quote_events(quote_id)",
            "CREATE INDEX IF NOT EXISTS idx_payments_status ON subscription_payments(status)",
        ]:
            cur.execute(sql)

        # Très important : CREATE/ALTER TABLE sont transactionnels avec psycopg2.
        # On valide ici afin que les autres workers Gunicorn voient immédiatement
        # les tables et migrations.
        conn.commit()
        cur.close()
        DB_READY = True
    except Exception:
        conn.rollback()
        raise
    finally:
        DB_POOL.putconn(conn)


def get_conn():
    db_init()
    return DB_POOL.getconn()


def query(sql, params=(), one=False, commit=False):
    # Une connexion PostgreSQL peut devenir invalide après une longue période
    # d'inactivité. On la remplace une fois avant d'abandonner la requête.
    last_error = None
    for attempt in range(2):
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            if commit:
                conn.commit()
            if cur.description:
                cols = [d[0] for d in cur.description]
                rows = [dict(zip(cols, r)) for r in cur.fetchall()]
                cur.close()
                DB_POOL.putconn(conn)
                return rows[0] if rows and one else (None if one else rows)
            cur.close()
            DB_POOL.putconn(conn)
            return None
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as exc:
            last_error = exc
            try:
                conn.rollback()
            except Exception:
                pass
            DB_POOL.putconn(conn, close=True)
            if attempt == 1:
                raise
        except Exception:
            conn.rollback()
            DB_POOL.putconn(conn)
            raise
    raise last_error


def execute(sql, params=(), returning=False):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        result = None
        if returning:
            result = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        DB_POOL.putconn(conn)


# ----------------------------
# Helpers
# ----------------------------

def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def money(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0.00")


def esc(value):
    return "" if value is None else str(value)


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    try:
        user = query("SELECT * FROM users WHERE id=%s", (uid,), one=True)
    except Exception:
        app.logger.exception("ERREUR_CURRENT_USER user_id=%s", uid)
        session.clear()
        return None
    # Compatibilité avec d'anciens comptes : active doit être TRUE par défaut.
    if not user or not user.get("active", True):
        session.clear()
        return None
    return user


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash("Connectez-vous pour continuer.", "warning")
            return redirect(url_for("connexion", next=request.path))
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        ensure_admin()
        user = current_user()
        if not user or user["role"] != "admin":
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def check_csrf():
    token = request.form.get("csrf", "")
    if not token or token != session.get("csrf"):
        abort(400, description="Jeton CSRF invalide.")


def plan_for(user_id):
    sub = query("SELECT * FROM subscriptions WHERE user_id=%s ORDER BY id DESC LIMIT 1", (user_id,), one=True)
    if not sub:
        return "free", PLANS["free"]
    plan = sub["plan"] if sub["plan"] in PLANS else "free"
    if sub["status"] != "active":
        return "free", PLANS["free"]
    if sub["expires_at"] and sub["expires_at"] < now():
        return "free", PLANS["free"]
    return plan, PLANS[plan]


def can_create_quote(user_id):
    plan_name, plan = plan_for(user_id)
    if plan["quotes"] is None:
        return True
    count = query("SELECT COUNT(*) AS n FROM quotes WHERE user_id=%s AND date_trunc('month', created_at)=date_trunc('month', CURRENT_TIMESTAMP)", (user_id,), one=True)["n"]
    return count < plan["quotes"]


def can_create_customer(user_id):
    _, plan = plan_for(user_id)
    if plan["clients"] is None:
        return True
    count = query("SELECT COUNT(*) AS n FROM customers WHERE user_id=%s", (user_id,), one=True)["n"]
    return count < plan["clients"]


def add_event(quote_id, event_type, message="", ip=None):
    execute("INSERT INTO quote_events(quote_id,event_type,message,ip_address) VALUES(%s,%s,%s,%s)", (quote_id, event_type, message, ip))


def notify(user_id, title, message):
    execute("INSERT INTO notifications(user_id,title,message) VALUES(%s,%s,%s)", (user_id, title, message))


def quote_number(user_id):
    row = query("SELECT COUNT(*) AS n FROM quotes WHERE user_id=%s", (user_id,), one=True)
    return f"DC-{datetime.now().year}-{int(row['n']) + 1:05d}"


def quote_url(token):
    return url_for("public_quote", token=token, _external=True)


def whatsapp_link(phone, text):
    digits = re.sub(r"\D", "", phone or "")
    encoded_text = text.replace(" ", "%20").replace("\n", "%0A")
    return f"https://wa.me/{digits}?text={encoded_text}" if digits else "#"


def html_page(title, content, user=None):
    csrf = csrf_token()
    nav = ""
    if user:
        nav = f'''<a href="/dashboard">Dashboard</a><a href="/nouveau-devis">Nouveau devis</a><a href="/clients">Clients</a><a href="/abonnement">Abonnement</a><a href="/profil">Profil</a>'''
        if user["role"] == "admin":
            nav += '<a href="/admin">Admin</a>'
        nav += '<a href="/deconnexion">Déconnexion</a>'
    else:
        nav = '<a href="/tarifs">Tarifs</a><a href="/connexion">Connexion</a><a class="btn" href="/inscription">Créer un compte</a>'
    return render_template_string(BASE, title=title, content=content, nav=nav, csrf=csrf, user=user, owner_name=OWNER_NAME)


# ----------------------------
# Startup
# ----------------------------

def ensure_admin():
    global ADMIN_READY
    if ADMIN_READY:
        return
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        ADMIN_READY = True
        return
    try:
        user = query("SELECT id FROM users WHERE email=%s", (ADMIN_EMAIL,), one=True)
        if not user:
            uid = execute(
                "INSERT INTO users(email,password_hash,full_name,company_name,role,cgu_accepted,cgu_version,cgu_accepted_at) VALUES(%s,%s,%s,%s,'admin',TRUE,%s,CURRENT_TIMESTAMP) RETURNING id",
                (ADMIN_EMAIL, generate_password_hash(ADMIN_PASSWORD), OWNER_NAME, "Devis Closer", CGU_VERSION), returning=True
            )
            execute("INSERT INTO subscriptions(user_id,plan,status) VALUES(%s,'pro','active')", (uid,))
            execute("INSERT INTO payment_settings(user_id) VALUES(%s)", (uid,))
        else:
            execute("UPDATE users SET role='admin',active=TRUE WHERE email=%s", (ADMIN_EMAIL,))
        ADMIN_READY = True
    except Exception:
        app.logger.exception("Impossible d'initialiser le compte administrateur")
        raise


    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        return
    user = query("SELECT id FROM users WHERE email=%s", (ADMIN_EMAIL,), one=True)
    if not user:
        uid = execute(
            "INSERT INTO users(email,password_hash,full_name,company_name,role,cgu_accepted,cgu_version,cgu_accepted_at) VALUES(%s,%s,%s,%s,'admin',TRUE,%s,CURRENT_TIMESTAMP) RETURNING id",
            (ADMIN_EMAIL, generate_password_hash(ADMIN_PASSWORD), OWNER_NAME, "Devis Closer", CGU_VERSION), returning=True
        )
        execute("INSERT INTO subscriptions(user_id,plan,status) VALUES(%s,'pro','active')", (uid,))
    else:
        execute("UPDATE users SET role='admin' WHERE email=%s", (ADMIN_EMAIL,))


# ----------------------------
# Public
# ----------------------------

@app.route("/health")
def health():
    try:
        query("SELECT 1", one=True)
        return "OK — Devis Closer", 200
    except Exception as exc:
        return f"DB ERROR: {exc}", 503


@app.route("/")
def accueil():
    return html_page("Devis Closer", '''
    <section class="hero">
      <div class="badge">DEVIS CLOSER</div>
      <h1>Transformez vos devis en contrats.</h1>
      <p>Créez, envoyez, suivez, relancez, négociez, faites signer et enregistrez les paiements de vos devis depuis une seule plateforme.</p>
      <div class="actions"><a class="btn primary" href="/inscription">Commencer gratuitement</a><a class="btn" href="/tarifs">Voir les tarifs</a></div>
    </section>
    <section class="grid three">
      <div class="card"><b>01 — Créer</b><p>Devis professionnels, numérotation automatique et calcul des totaux.</p></div>
      <div class="card"><b>02 — Closer</b><p>Lien public, suivi des événements, relances et aide à la négociation.</p></div>
      <div class="card"><b>03 — Contracter</b><p>Acceptation, signature électronique et parcours de paiement.</p></div>
    </section>
    <section class="card center"><h2>Un devis ne doit pas rester sans réponse.</h2><p>Devis Closer est conçu pour réduire les frictions entre votre offre et la signature.</p></section>
    ''', current_user())


@app.route("/tarifs")
def tarifs():
    cards = ""
    for key, plan in PLANS.items():
        features = "".join(f"<li>{esc(f)}</li>" for f in plan["features"])
        popular = '<span class="tag">POPULAIRE</span>' if key == "pro" else ""
        price = "Gratuit" if key == "free" else f"{plan['price']:,.0f} XOF/mois".replace(",", " ")
        cards += f'''<div class="card plan {"featured" if key == "pro" else ""}">{popular}<h2>{plan["name"]}</h2><div class="price">{price}</div><ul>{features}</ul><a class="btn primary" href="/inscription?plan={key}">{"Commencer" if key=="free" else "Choisir " + plan["name"]}</a></div>'''
    return html_page("Tarifs", f'<section><h1>Des plans simples.</h1><div class="grid three">{cards}</div></section>', current_user())


@app.route("/inscription", methods=["GET", "POST"])
def inscription():
    if request.method == "POST":
        check_csrf()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        name = request.form.get("full_name", "").strip()
        company = request.form.get("company_name", "").strip()
        phone = request.form.get("phone", "").strip()
        country = request.form.get("country", "").strip()
        currency = request.form.get("currency", "XOF").strip().upper()
        accepted = request.form.get("cgu") == "on"
        if not accepted:
            flash("Vous devez accepter les CGU.", "danger")
            return redirect(url_for("inscription"))
        if not name or not email or len(password) < 8:
            flash("Nom, email et mot de passe de 8 caractères minimum sont obligatoires.", "danger")
            return redirect(url_for("inscription"))
        try:
            if query("SELECT id FROM users WHERE LOWER(email)=LOWER(%s)", (email,), one=True):
                flash("Cet email est déjà utilisé.", "danger")
                return redirect(url_for("connexion"))
            uid = execute(
                "INSERT INTO users(email,password_hash,full_name,company_name,phone,country,currency,cgu_accepted,cgu_version,cgu_accepted_at) VALUES(%s,%s,%s,%s,%s,%s,%s,TRUE,%s,CURRENT_TIMESTAMP) RETURNING id",
                (email, generate_password_hash(password), name, company, phone, country, currency, CGU_VERSION), returning=True
            )
            execute("INSERT INTO subscriptions(user_id,plan,status) VALUES(%s,'free','active')", (uid,))
            execute("INSERT INTO payment_settings(user_id) VALUES(%s)", (uid,))
        except psycopg2.errors.UniqueViolation:
            flash("Cet email est déjà utilisé.", "danger")
            return redirect(url_for("connexion"))
        except psycopg2.Error:
            app.logger.exception("Erreur PostgreSQL lors de l'inscription")
            flash("Impossible de créer le compte pour le moment. Vérifiez la connexion à la base PostgreSQL.", "danger")
            return redirect(url_for("inscription"))
        session.clear()
        session["user_id"] = uid
        session["csrf"] = secrets.token_urlsafe(32)
        flash("Compte créé. Bienvenue sur Devis Closer !", "success")
        return redirect(url_for("dashboard"))
    country_options = "".join(f'<option value="{code}">{name}</option>' for code, name in COUNTRIES)
    currency_options = "".join(f'<option value="{c}">{c}</option>' for c in CURRENCIES)
    return html_page("Créer un compte", f'''
    <section class="formbox"><h1>Créer votre compte</h1><p>Commencez avec le plan Free.</p>
    <form method="post"><input type="hidden" name="csrf" value="{csrf_token()}">
      <label>Nom complet<input name="full_name" required></label>
      <label>Entreprise / activité<input name="company_name"></label>
      <label>Email<input type="email" name="email" required></label>
      <label>Téléphone / WhatsApp<input name="phone"></label>
      <label>Pays<select name="country"><option value="">Sélectionner</option>{country_options}</select></label>
      <label>Devise principale<select name="currency">{currency_options}</select></label>
      <label>Mot de passe<input type="password" name="password" minlength="8" required></label>
      <label class="check"><input type="checkbox" name="cgu" required> J'ai lu et j'accepte les <a href="/cgu" target="_blank">Conditions Générales d'Utilisation</a>.</label>
      <button class="btn primary full">Créer mon compte</button>
    </form></section>''', None)


@app.route("/connexion", methods=["GET", "POST"])
def connexion():
    if request.method == "POST":
        check_csrf()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        # Étape 1 : récupérer le compte. On ne charge pas toutes les colonnes
        # avant d'avoir validé les identifiants.
        try:
            user = query(
                "SELECT id, password_hash, COALESCE(active, TRUE) AS active "
                "FROM users WHERE LOWER(email)=LOWER(%s) LIMIT 1",
                (email,), one=True
            )
        except psycopg2.Error as exc:
            app.logger.exception("ERREUR_DB_LOGIN email=%s: %s", email, exc)
            flash("La base de données est momentanément indisponible. Réessayez dans quelques secondes.", "danger")
            return redirect(url_for("connexion"))
        except Exception as exc:
            app.logger.exception("ERREUR_LOGIN_LECTURE type=%s email=%s: %s", type(exc).__name__, email, exc)
            flash("Impossible de vous connecter pour le moment. Réessayez dans quelques secondes.", "danger")
            return redirect(url_for("connexion"))

        if not user:
            flash("Email ou mot de passe incorrect.", "danger")
            return redirect(url_for("connexion"))

        if not user.get("active", True):
            flash("Ce compte est désactivé. Contactez l'administrateur.", "danger")
            return redirect(url_for("connexion"))

        # Étape 2 : vérifier le mot de passe sans laisser une erreur de hash
        # transformer une simple mauvaise authentification en erreur technique.
        stored_hash = user.get("password_hash")
        if not stored_hash:
            app.logger.error("ERREUR_LOGIN_HASH_VIDE user_id=%s", user.get("id"))
            flash("Ce compte ne possède pas de mot de passe valide. Utilisez « Mot de passe oublié ? ».", "danger")
            return redirect(url_for("connexion"))

        try:
            password_ok = check_password_hash(stored_hash, password)
        except Exception as exc:
            app.logger.exception("ERREUR_LOGIN_HASH type=%s user_id=%s: %s", type(exc).__name__, user.get("id"), exc)
            flash("Le mot de passe enregistré pour ce compte doit être réinitialisé. Utilisez « Mot de passe oublié ? ».", "danger")
            return redirect(url_for("connexion"))

        if not password_ok:
            flash("Email ou mot de passe incorrect.", "danger")
            return redirect(url_for("connexion"))

        # Étape 3 : ouvrir la session. Les autres données du profil sont
        # chargées uniquement après authentification réussie.
        try:
            session.clear()
            session["user_id"] = user["id"]
            session["csrf"] = secrets.token_urlsafe(32)
        except Exception as exc:
            app.logger.exception("ERREUR_SESSION_LOGIN user_id=%s: %s", user.get("id"), exc)
            flash("Impossible d'ouvrir votre session pour le moment. Réessayez.", "danger")
            return redirect(url_for("connexion"))

        return redirect(request.args.get("next") or url_for("dashboard"))
    return html_page("Connexion", f'''
    <section class="formbox"><h1>Connexion</h1><form method="post"><input type="hidden" name="csrf" value="{csrf_token()}">
      <label>Email<input type="email" name="email" required></label>
      <label>Mot de passe<input type="password" name="password" required></label>
      <button class="btn primary full">Se connecter</button>
    </form><p><a href="/mot-de-passe-oublie">Mot de passe oublié ?</a></p></section>''', None)


@app.route("/deconnexion")
def deconnexion():
    session.clear()
    return redirect(url_for("accueil"))


@app.route("/mot-de-passe-oublie", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        check_csrf()
        email = request.form.get("email", "").strip().lower()
        user = query("SELECT id FROM users WHERE email=%s", (email,), one=True)
        if user:
            token = secrets.token_urlsafe(32)
            digest = hashlib.sha256(token.encode()).hexdigest()
            # La table password_resets est créée par db_init().
            execute("INSERT INTO password_resets(user_id,token_hash,expires_at) VALUES(%s,%s,%s)", (user["id"], digest, now() + timedelta(minutes=30)))
            link = url_for("reset_password", token=token, _external=True)
            flash(f"Lien de réinitialisation (à envoyer à l'utilisateur) : {link}", "success")
        else:
            flash("Si le compte existe, une procédure de réinitialisation est disponible.", "success")
        return redirect(url_for("forgot_password"))
    return html_page("Mot de passe oublié", f'''<section class="formbox"><h1>Mot de passe oublié</h1><form method="post"><input type="hidden" name="csrf" value="{csrf_token()}"><label>Email<input type="email" name="email" required></label><button class="btn primary full">Générer le lien</button></form></section>''', None)


@app.route("/reset/<token>", methods=["GET", "POST"])
def reset_password(token):
    digest = hashlib.sha256(token.encode()).hexdigest()
    row = query("SELECT * FROM password_resets WHERE token_hash=%s AND used=FALSE AND expires_at>CURRENT_TIMESTAMP ORDER BY id DESC LIMIT 1", (digest,), one=True)
    if not row:
        abort(400, description="Lien invalide ou expiré.")
    if request.method == "POST":
        check_csrf()
        pwd = request.form.get("password", "")
        if len(pwd) < 8:
            flash("Le mot de passe doit contenir au moins 8 caractères.", "danger")
            return redirect(request.url)
        execute("UPDATE users SET password_hash=%s WHERE id=%s", (generate_password_hash(pwd), row["user_id"]))
        execute("UPDATE password_resets SET used=TRUE WHERE id=%s", (row["id"],))
        flash("Mot de passe modifié.", "success")
        return redirect(url_for("connexion"))
    return html_page("Nouveau mot de passe", f'''<section class="formbox"><h1>Nouveau mot de passe</h1><form method="post"><input type="hidden" name="csrf" value="{csrf_token()}"><label>Nouveau mot de passe<input type="password" name="password" minlength="8" required></label><button class="btn primary full">Enregistrer</button></form></section>''', None)


@app.route("/cgu")
def cgu():
    return html_page("CGU", '''
    <section class="card prose"><h1>Conditions Générales d'Utilisation</h1>
    <p><b>Version 1.0</b></p>
    <h2>1. Objet</h2><p>Devis Closer fournit un logiciel permettant de créer, transmettre, suivre, relancer, faire accepter et signer des devis, ainsi que d'enregistrer des informations relatives aux paiements.</p>
    <h2>2. Responsabilité de l'utilisateur</h2><p>L'utilisateur reste responsable de ses produits, services, prix, taxes, devis, clients, obligations contractuelles et communications.</p>
    <h2>3. Paiements d'abonnement</h2><p>Les abonnements Starter et Pro sont des abonnements mensuels. Chaque période d'abonnement dure 30 jours à compter de sa validation. Pour continuer à utiliser les fonctionnalités payantes après expiration, l'utilisateur doit renouveler son abonnement et effectuer un nouveau paiement mensuel. Le paiement peut être soumis à une vérification manuelle, notamment pour MoMo et certaines cryptomonnaies.</p>
    <h2>4. Paiements des devis</h2><p>Pour le MVP, le client paie directement le professionnel sur les coordonnées de paiement indiquées par celui-ci. Devis Closer ne détient ni ne conserve les fonds du client pour le compte du professionnel.</p>
    <h2>5. Commission de service de 2%</h2><p>Une commission de service de 2% est calculée sur le montant des paiements de devis enregistrés dans la plateforme. Dans le modèle MVP de paiement direct, cette commission est enregistrée comme montant dû au titre du service et n'est pas automatiquement prélevée sur le transfert direct effectué au professionnel.</p>
    <h2>6. Signature électronique</h2><p>La plateforme conserve le nom du signataire, la date et l'heure, ainsi que des informations techniques utiles à la traçabilité. L'utilisateur doit respecter les lois applicables.</p>
    <h2>7. Fraude et litiges</h2><p>Tout faux justificatif, transaction contestée ou usage frauduleux peut entraîner une suspension. Les litiges commerciaux entre professionnel et client restent entre leurs parties, sous réserve des obligations légales de Devis Closer.</p>
    <h2>8. Données et sécurité</h2><p>Devis Closer met en œuvre des mesures raisonnables de sécurité. L'utilisateur doit protéger ses identifiants et ne pas transmettre de données qu'il n'est pas autorisé à traiter.</p>
    <h2>9. Suspension et suppression</h2><p>Un compte peut être suspendu en cas d'abus, fraude, violation des présentes conditions ou obligation légale.</p>
    <h2>10. Évolution</h2><p>Les fonctionnalités, tarifs et CGU peuvent évoluer. La version acceptée est conservée avec sa date d'acceptation.</p>
    <h2>11. Droit applicable</h2><p>Les règles applicables et le règlement des différends seront précisés selon la juridiction de l'opérateur et les obligations légales applicables.</p>
    </section>''', current_user())


# ----------------------------
# Dashboard / profile
# ----------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    plan_name, plan = plan_for(user["id"])
    stats = query("""SELECT
        COUNT(*) AS total,
        COUNT(*) FILTER (WHERE status='sent') AS sent,
        COUNT(*) FILTER (WHERE status='viewed') AS viewed,
        COUNT(*) FILTER (WHERE status='negotiation') AS negotiation,
        COUNT(*) FILTER (WHERE status='accepted') AS accepted,
        COUNT(*) FILTER (WHERE status='signed') AS signed,
        COUNT(*) FILTER (WHERE status='paid') AS paid,
        COUNT(*) FILTER (WHERE status='refused') AS refused,
        COUNT(*) FILTER (WHERE status='expired') AS expired,
        COALESCE(SUM(total) FILTER (WHERE status IN ('accepted','signed','paid')),0) AS potential,
        COALESCE(SUM(total) FILTER (WHERE status='paid'),0) AS won
        FROM quotes WHERE user_id=%s""", (user["id"],), one=True)
    conversion = (Decimal(str(stats["accepted"] or 0)) / Decimal(str(stats["total"] or 1)) * 100).quantize(Decimal("0.1"))
    quotes = query("SELECT q.*, c.name AS customer_name FROM quotes q LEFT JOIN customers c ON c.id=q.customer_id WHERE q.user_id=%s ORDER BY q.id DESC LIMIT 10", (user["id"],))
    rows = "".join(f'''<tr><td><a href="/devis/{q['id']}">{esc(q['quote_number'])}</a></td><td>{esc(q['customer_name'])}</td><td>{esc(q['total'])} {esc(q['currency'])}</td><td><span class="status">{esc(q['status'])}</span></td><td><a href="/devis/{q['id']}">Ouvrir</a></td></tr>''' for q in quotes)
    return html_page("Dashboard", f'''
    <section><div class="topline"><div><div class="badge">{plan["name"].upper()}</div><h1>Bonjour {esc(user["full_name"])}</h1><p>Transformez vos devis en contrats.</p></div><a class="btn primary" href="/nouveau-devis">+ Nouveau devis</a></div>
    <div class="stats">{stat("Chiffre potentiel", f"{stats['potential']} {user['currency']}")}{stat("Gagné", f"{stats['won']} {user['currency']}")}{stat("Devis", stats['total'])}{stat("Acceptation", f"{conversion}%")}</div>
    <div class="grid three"><div class="card"><h3>Suivi</h3><p>Envoyés: {stats['sent']} · Vus: {stats['viewed']} · Négociation: {stats['negotiation']}</p><p>Acceptés: {stats['accepted']} · Signés: {stats['signed']} · Payés: {stats['paid']}</p></div><div class="card"><h3>Relances</h3><p>Utilisez le lien public et WhatsApp pour relancer rapidement vos prospects.</p><a href="/relances" class="btn">Voir les relances</a></div><div class="card"><h3>AI Closer</h3><p>{"Disponible avec Pro." if plan_name != "pro" else "Analysez vos prospects et obtenez une prochaine action commerciale."}</p><a href="/ai-closer" class="btn">Ouvrir</a></div></div>
    <div class="card"><h2>Derniers devis</h2><div class="tablewrap"><table><tr><th>Numéro</th><th>Client</th><th>Total</th><th>Statut</th><th></th></tr>{rows or '<tr><td colspan="5">Aucun devis pour le moment.</td></tr>'}</table></div></div></section>''', user)


def stat(label, value):
    return f'<div class="stat"><small>{label}</small><strong>{esc(value)}</strong></div>'


@app.route("/profil", methods=["GET", "POST"])
@login_required
def profil():
    user = current_user()
    if request.method == "POST":
        check_csrf()
        execute("UPDATE users SET full_name=%s,company_name=%s,phone=%s,address=%s,country=%s,currency=%s,language=%s,timezone=%s WHERE id=%s", (
            request.form.get("full_name", "").strip(), request.form.get("company_name", "").strip(), request.form.get("phone", "").strip(), request.form.get("address", "").strip(), request.form.get("country", "").strip(), request.form.get("currency", "XOF").strip().upper(), request.form.get("language", "fr"), request.form.get("timezone", "Africa/Porto-Novo"), user["id"]))
        flash("Profil mis à jour.", "success")
        return redirect(url_for("profil"))
    return html_page("Profil", f'''<section class="formbox"><h1>Mon profil</h1><form method="post"><input type="hidden" name="csrf" value="{csrf_token()}">
      <label>Nom complet<input name="full_name" value="{esc(user['full_name'])}" required></label><label>Entreprise<input name="company_name" value="{esc(user['company_name'])}"></label><label>Téléphone<input name="phone" value="{esc(user['phone'])}"></label><label>Adresse<textarea name="address">{esc(user['address'])}</textarea></label><label>Pays<input name="country" value="{esc(user['country'])}"></label><label>Devise<input name="currency" value="{esc(user['currency'])}"></label><label>Langue<select name="language"><option value="fr">Français</option><option value="en">English</option><option value="es">Español</option><option value="pt">Português</option><option value="de">Deutsch</option><option value="it">Italiano</option></select></label><label>Fuseau horaire<input name="timezone" value="{esc(user['timezone'])}"></label><button class="btn primary full">Enregistrer</button></form></section>''', user)


# ----------------------------
# Customers
# ----------------------------

@app.route("/clients", methods=["GET", "POST"])
@login_required
def clients():
    user = current_user()
    if request.method == "POST":
        check_csrf()
        if not can_create_customer(user["id"]):
            flash("La limite de clients de votre plan est atteinte.", "warning")
            return redirect(url_for("abonnement"))
        execute("INSERT INTO customers(user_id,name,company,email,phone,address,country,notes) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", (user["id"], request.form.get("name", "").strip(), request.form.get("company", "").strip(), request.form.get("email", "").strip(), request.form.get("phone", "").strip(), request.form.get("address", "").strip(), request.form.get("country", "").strip(), request.form.get("notes", "").strip()))
        flash("Client ajouté.", "success")
        return redirect(url_for("clients"))
    rows = query("SELECT * FROM customers WHERE user_id=%s ORDER BY id DESC", (user["id"],))
    table = "".join(f'<tr><td>{esc(c["name"])}</td><td>{esc(c["company"])}</td><td>{esc(c["email"])}</td><td>{esc(c["phone"])}</td><td><a href="/client/{c["id"]}">Ouvrir</a></td></tr>' for c in rows)
    return html_page("Clients", f'''<section><div class="topline"><h1>Clients</h1><a class="btn" href="#ajouter">+ Ajouter</a></div><div class="card"><div class="tablewrap"><table><tr><th>Nom</th><th>Entreprise</th><th>Email</th><th>Téléphone</th><th></th></tr>{table or '<tr><td colspan="5">Aucun client.</td></tr>'}</table></div></div><div id="ajouter" class="formbox"><h2>Nouveau client</h2><form method="post"><input type="hidden" name="csrf" value="{csrf_token()}"><label>Nom<input name="name" required></label><label>Entreprise<input name="company"></label><label>Email<input type="email" name="email"></label><label>Téléphone<input name="phone"></label><label>Adresse<input name="address"></label><label>Pays<input name="country"></label><label>Notes<textarea name="notes"></textarea></label><button class="btn primary full">Ajouter</button></form></div></section>''', user)


@app.route("/client/<int:cid>")
@login_required
def client_detail(cid):
    user = current_user()
    c = query("SELECT * FROM customers WHERE id=%s AND user_id=%s", (cid, user["id"]), one=True)
    if not c: abort(404)
    quotes = query("SELECT * FROM quotes WHERE customer_id=%s AND user_id=%s ORDER BY id DESC", (cid, user["id"]))
    items = "".join(f'<li><a href="/devis/{q["id"]}">{esc(q["quote_number"])}</a> — {esc(q["total"])} {esc(q["currency"])} — {esc(q["status"])}</li>' for q in quotes)
    return html_page("Client", f'<section><div class="card"><h1>{esc(c["name"])}</h1><p>{esc(c["company"])}</p><p>{esc(c["email"])} · {esc(c["phone"])}</p><p>{esc(c["address"])}</p><h2>Historique</h2><ul>{items or "<li>Aucun devis.</li>"}</ul></div></section>', user)


# ----------------------------
# Quotes
# ----------------------------

@app.route("/nouveau-devis", methods=["GET", "POST"])
@login_required
def nouveau_devis():
    user = current_user()
    if request.method == "POST":
        check_csrf()
        if not can_create_quote(user["id"]):
            flash("La limite de devis de votre plan est atteinte.", "warning")
            return redirect(url_for("abonnement"))
        customer_id = request.form.get("customer_id") or None
        if customer_id:
            customer = query("SELECT id FROM customers WHERE id=%s AND user_id=%s", (customer_id, user["id"]), one=True)
            if not customer: abort(403)
        descs = request.form.getlist("item_desc")
        qtys = request.form.getlist("item_qty")
        prices = request.form.getlist("item_price")
        lines = []
        subtotal = Decimal("0.00")
        for i, desc in enumerate(descs):
            desc = desc.strip()
            if not desc: continue
            qty = money(qtys[i] if i < len(qtys) else 1)
            price = money(prices[i] if i < len(prices) else 0)
            if qty <= 0: qty = Decimal("1.00")
            total = (qty * price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            lines.append((desc, qty, price, total))
            subtotal += total
        discount = money(request.form.get("discount", "0"))
        tax_rate = money(request.form.get("tax", "0"))
        base = max(Decimal("0.00"), subtotal - discount)
        tax = (base * tax_rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total = base + tax
        token = secrets.token_urlsafe(32)
        expires = request.form.get("expires_at") or None
        qid = execute("INSERT INTO quotes(user_id,customer_id,quote_number,public_token,description,currency,subtotal,discount,tax,total,terms,status,expires_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'draft',%s) RETURNING id", (user["id"], customer_id, quote_number(user["id"]), token, request.form.get("description", "").strip(), request.form.get("currency", user["currency"]).upper(), subtotal, discount, tax, total, request.form.get("terms", "").strip(), expires), returning=True)
        for line in lines:
            execute("INSERT INTO quote_items(quote_id,description,quantity,unit_price,line_total) VALUES(%s,%s,%s,%s,%s)", (qid, *line))
        add_event(qid, "created", "Devis créé", request.remote_addr)
        flash("Devis créé.", "success")
        return redirect(url_for("devis_detail", qid=qid))
    customers = query("SELECT id,name,company FROM customers WHERE user_id=%s ORDER BY name", (user["id"],))
    opts = '<option value="">Client libre</option>' + ''.join(f'<option value="{c["id"]}">{esc(c["name"])} — {esc(c["company"])}</option>' for c in customers)
    return html_page("Nouveau devis", f'''
    <section class="formbox wide"><h1>Nouveau devis</h1><form method="post" id="quoteForm"><input type="hidden" name="csrf" value="{csrf_token()}">
      <label>Client<select name="customer_id">{opts}</select></label>
      <label>Devise<input name="currency" value="{esc(user['currency'])}"></label>
      <div id="items"><div class="itemrow"><input name="item_desc" placeholder="Produit / service" required><input name="item_qty" type="number" step="0.01" value="1" placeholder="Qté"><input name="item_price" type="number" step="0.01" value="0" placeholder="Prix"><button type="button" class="btn remove" onclick="this.parentElement.remove()">×</button></div></div>
      <button type="button" class="btn" onclick="addItem()">+ Ajouter une ligne</button>
      <div class="grid two"><label>Remise<input name="discount" type="number" step="0.01" value="0"></label><label>Taxe (%)<input name="tax" type="number" step="0.01" value="0"></label></div>
      <label>Description / introduction<textarea name="description"></textarea></label><label>Conditions<textarea name="terms">Validité du devis selon la date d'expiration indiquée.</textarea></label><label>Date d'expiration<input type="date" name="expires_at"></label>
      <button class="btn primary full">Créer le devis</button></form></section>
    <script>function addItem(){{const d=document.createElement('div');d.className='itemrow';d.innerHTML='<input name="item_desc" placeholder="Produit / service" required><input name="item_qty" type="number" step="0.01" value="1"><input name="item_price" type="number" step="0.01" value="0"><button type="button" class="btn remove" onclick="this.parentElement.remove()">×</button>';document.getElementById('items').appendChild(d);}}</script>''', user)


@app.route("/devis/<int:qid>")
@login_required
def devis_detail(qid):
    user = current_user()
    q = query("SELECT q.*, c.name AS customer_name,c.email AS customer_email,c.phone AS customer_phone,c.company AS customer_company FROM quotes q LEFT JOIN customers c ON c.id=q.customer_id WHERE q.id=%s AND q.user_id=%s", (qid, user["id"]), one=True)
    if not q: abort(404)
    items = query("SELECT * FROM quote_items WHERE quote_id=%s ORDER BY id", (qid,))
    events = query("SELECT * FROM quote_events WHERE quote_id=%s ORDER BY id DESC", (qid,))
    public = quote_url(q["public_token"])
    wa = whatsapp_link(q.get("customer_phone"), f"Bonjour, voici votre devis {q['quote_number']} : {public}")
    line_html = "".join(f'<tr><td>{esc(i["description"])}</td><td>{esc(i["quantity"])}</td><td>{esc(i["unit_price"])} {esc(q["currency"])}</td><td>{esc(i["line_total"])} {esc(q["currency"])}</td></tr>' for i in items)
    ev_html = "".join(f'<li><b>{esc(e["event_type"])}</b> — {esc(e["created_at"])} — {esc(e["message"])}</li>' for e in events)
    actions = f'''<form method="post" action="/devis/{qid}/envoyer"><input type="hidden" name="csrf" value="{csrf_token()}"><button class="btn primary">Marquer envoyé</button></form><a class="btn" href="{public}" target="_blank">Voir lien public</a><a class="btn" href="{wa}" target="_blank">WhatsApp</a><button class="btn" onclick="navigator.clipboard.writeText('{public}')">Copier le lien</button>'''
    if q["status"] in ("accepted", "signed"):
        actions += f'<a class="btn primary" href="/devis/{qid}/paiement">Enregistrer paiement</a>'
    return html_page("Devis", f'''
    <section><div class="topline"><div><div class="badge">{esc(q['status']).upper()}</div><h1>{esc(q['quote_number'])}</h1><p>{esc(q['customer_name']) or 'Client non renseigné'}</p></div><div class="actions">{actions}</div></div>
    <div class="card"><p>{esc(q['description'])}</p><div class="tablewrap"><table><tr><th>Désignation</th><th>Qté</th><th>Prix</th><th>Total</th></tr>{line_html}</table></div><div class="totals"><p>Sous-total: <b>{esc(q['subtotal'])} {esc(q['currency'])}</b></p><p>Remise: <b>{esc(q['discount'])} {esc(q['currency'])}</b></p><p>Taxe: <b>{esc(q['tax'])} {esc(q['currency'])}</b></p><h2>Total: {esc(q['total'])} {esc(q['currency'])}</h2></div><p>{esc(q['terms'])}</p></div>
    <div class="grid two"><div class="card"><h2>Timeline</h2><ul>{ev_html}</ul></div><div class="card"><h2>Relance</h2><p>Partagez le lien public avec votre client.</p><input value="{public}" readonly onclick="this.select()"></div></div></section>''', user)


@app.route("/devis/<int:qid>/envoyer", methods=["POST"])
@login_required
def send_quote(qid):
    check_csrf()
    user = current_user()
    q = query("SELECT * FROM quotes WHERE id=%s AND user_id=%s", (qid, user["id"]), one=True)
    if not q: abort(404)
    execute("UPDATE quotes SET status='sent',updated_at=CURRENT_TIMESTAMP WHERE id=%s", (qid,))
    add_event(qid, "sent", "Devis marqué comme envoyé", request.remote_addr)
    flash("Devis marqué comme envoyé.", "success")
    return redirect(url_for("devis_detail", qid=qid))


@app.route("/devis/<int:qid>/relancer", methods=["POST"])
@login_required
def relancer_quote(qid):
    check_csrf()
    user = current_user()
    q = query("SELECT q.*,c.phone FROM quotes q LEFT JOIN customers c ON c.id=q.customer_id WHERE q.id=%s AND q.user_id=%s", (qid, user["id"]), one=True)
    if not q: abort(404)
    add_event(qid, "followup", "Relance effectuée", request.remote_addr)
    flash("Relance enregistrée.", "success")
    return redirect(url_for("devis_detail", qid=qid))


# ----------------------------
# Public quote
# ----------------------------

@app.route("/q/<token>")
def public_quote(token):
    q = query("SELECT q.*,u.full_name,u.company_name,u.email AS professional_email,u.phone AS professional_phone FROM quotes q JOIN users u ON u.id=q.user_id WHERE q.public_token=%s", (token,), one=True)
    if not q: abort(404)
    if q["status"] == "expired" or (q["expires_at"] and q["expires_at"] < datetime.now().date() and q["status"] not in ("accepted", "signed", "paid")):
        execute("UPDATE quotes SET status='expired' WHERE id=%s", (q["id"],))
        q["status"] = "expired"
    if q["status"] == "draft":
        execute("UPDATE quotes SET status='sent' WHERE id=%s", (q["id"],))
        add_event(q["id"], "sent", "Lien public consulté: devis envoyé", request.remote_addr)
    elif q["status"] in ("sent",):
        execute("UPDATE quotes SET status='viewed' WHERE id=%s", (q["id"],))
        add_event(q["id"], "viewed", "Devis consulté", request.remote_addr)
    items = query("SELECT * FROM quote_items WHERE quote_id=%s ORDER BY id", (q["id"],))
    payment_settings = query("SELECT * FROM payment_settings WHERE user_id=%s", (q["user_id"],), one=True)
    rows = "".join(f'<tr><td>{esc(i["description"])}</td><td>{esc(i["quantity"])}</td><td>{esc(i["unit_price"])} {esc(q["currency"])}</td><td>{esc(i["line_total"])} {esc(q["currency"])}</td></tr>' for i in items)
    actions = ''
    if q["status"] not in ("refused", "expired", "paid"):
        actions = f'''<div class="actions"><form method="post" action="/q/{token}/accept"><input type="hidden" name="csrf" value="{csrf_token()}"><button class="btn primary">Accepter le devis</button></form><a class="btn" href="/q/{token}/payer">Accepter et payer</a><a class="btn" href="/q/{token}/changer">Demander une modification</a><form method="post" action="/q/{token}/refuse"><input type="hidden" name="csrf" value="{csrf_token()}"><button class="btn danger">Refuser</button></form></div>'''
    return render_template_string(PUBLIC, title=q["quote_number"], q=q, rows=rows, actions=actions, settings=payment_settings, csrf=csrf_token())


@app.route("/q/<token>/accept", methods=["POST"])
def public_accept(token):
    check_csrf()
    q = query("SELECT * FROM quotes WHERE public_token=%s", (token,), one=True)
    if not q: abort(404)
    execute("UPDATE quotes SET status='accepted',updated_at=CURRENT_TIMESTAMP WHERE id=%s", (q["id"],))
    add_event(q["id"], "accepted", "Devis accepté par le client", request.remote_addr)
    notify(q["user_id"], "Devis accepté", f"Le devis {q['quote_number']} a été accepté.")
    return redirect(url_for("public_quote", token=token))


@app.route("/q/<token>/refuse", methods=["POST"])
def public_refuse(token):
    check_csrf()
    q = query("SELECT * FROM quotes WHERE public_token=%s", (token,), one=True)
    if not q: abort(404)
    execute("UPDATE quotes SET status='refused',updated_at=CURRENT_TIMESTAMP WHERE id=%s", (q["id"],))
    add_event(q["id"], "refused", "Devis refusé par le client", request.remote_addr)
    notify(q["user_id"], "Devis refusé", f"Le devis {q['quote_number']} a été refusé.")
    return redirect(url_for("public_quote", token=token))


@app.route("/q/<token>/changer", methods=["GET", "POST"])
def public_change(token):
    q = query("SELECT * FROM quotes WHERE public_token=%s", (token,), one=True)
    if not q: abort(404)
    if request.method == "POST":
        check_csrf()
        msg = request.form.get("message", "").strip()
        add_event(q["id"], "negotiation", msg or "Demande de modification", request.remote_addr)
        execute("UPDATE quotes SET status='negotiation',updated_at=CURRENT_TIMESTAMP WHERE id=%s", (q["id"],))
        notify(q["user_id"], "Demande de modification", f"Le client a demandé une modification pour {q['quote_number']}.")
        return redirect(url_for("public_quote", token=token))
    return render_template_string(PUBLIC_SIMPLE, title="Demander une modification", heading="Que souhaitez-vous modifier ?", body=f'''<form method="post"><input type="hidden" name="csrf" value="{csrf_token()}"><textarea name="message" required placeholder="Votre demande"></textarea><button class="btn primary full">Envoyer la demande</button></form>''')


@app.route("/q/<token>/signer", methods=["GET", "POST"])
def public_sign(token):
    q = query("SELECT * FROM quotes WHERE public_token=%s", (token,), one=True)
    if not q: abort(404)
    if request.method == "POST":
        check_csrf()
        name = request.form.get("signer_name", "").strip()
        email = request.form.get("signer_email", "").strip()
        if not name: abort(400)
        execute("INSERT INTO signatures(quote_id,signer_name,signer_email,signature_text,ip_address) VALUES(%s,%s,%s,%s,%s)", (q["id"], name, email, name, request.remote_addr))
        execute("UPDATE quotes SET status='signed',updated_at=CURRENT_TIMESTAMP WHERE id=%s", (q["id"],))
        add_event(q["id"], "signed", f"Signature électronique: {name}", request.remote_addr)
        notify(q["user_id"], "Devis signé", f"Le devis {q['quote_number']} vient d'être signé.")
        return redirect(url_for("public_quote", token=token))
    return render_template_string(PUBLIC_SIMPLE, title="Signer", heading="Signature électronique", body=f'''<form method="post"><input type="hidden" name="csrf" value="{csrf_token()}"><label>Nom complet<input name="signer_name" required></label><label>Email<input type="email" name="signer_email"></label><p>En validant, vous confirmez votre volonté de signer le devis.</p><button class="btn primary full">Signer le devis</button></form>''')


@app.route("/q/<token>/payer", methods=["GET", "POST"])
def public_pay(token):
    q = query("SELECT q.*,u.full_name,u.company_name FROM quotes q JOIN users u ON u.id=q.user_id WHERE q.public_token=%s", (token,), one=True)
    if not q: abort(404)
    settings = query("SELECT * FROM payment_settings WHERE user_id=%s", (q["user_id"],), one=True)
    if request.method == "POST":
        check_csrf()
        method = request.form.get("payment_method", "MoMo")
        txid = request.form.get("transaction_id", "").strip() or None
        proof = request.files.get("proof")
        data = proof.read() if proof and proof.filename else None
        mime = proof.mimetype if proof and proof.filename else None
        if data and len(data) > 2 * 1024 * 1024: abort(413)
        commission = (money(q["total"]) * Decimal("0.02")).quantize(Decimal("0.01"))
        net = money(q["total"]) - commission
        try:
            execute("INSERT INTO quote_payments(quote_id,professional_id,gross_amount,commission_amount,net_amount,currency,payment_method,transaction_id,proof_data,proof_mime,status) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending')", (q["id"], q["user_id"], q["total"], commission, net, q["currency"], method, txid, data, mime))
        except psycopg2.errors.UniqueViolation:
            flash("Cet identifiant de transaction est déjà utilisé.", "danger")
            return redirect(request.url)
        execute("UPDATE quotes SET status='paid',updated_at=CURRENT_TIMESTAMP WHERE id=%s", (q["id"],))
        add_event(q["id"], "payment_submitted", "Paiement déclaré par le client", request.remote_addr)
        notify(q["user_id"], "Paiement déclaré", f"Un paiement a été déclaré pour {q['quote_number']}. Commission de service calculée: {commission} {q['currency']}.")
        return render_template_string(PUBLIC_SIMPLE, title="Paiement enregistré", heading="Paiement enregistré", body=f'<div class="card"><h2>Merci.</h2><p>Le paiement a été enregistré. Le montant a été payé directement au professionnel selon les coordonnées affichées.</p><p>Commission de service Devis Closer: <b>{commission} {esc(q["currency"])}</b>.</p><a class="btn primary" href="/q/{token}">Retour au devis</a></div>')
    payment_html = ""
    if settings:
        payment_html = f'''<div class="card"><h3>Paiement direct au professionnel</h3><p><b>{esc(q['full_name'])}</b></p><p>MoMo: {esc(settings['momo_number'])} — {esc(settings['momo_name'])}</p><p>USDT TRC20: <code>{esc(settings['usdt_trc20'])}</code></p><p>USDT BEP20: <code>{esc(settings['usdt_bep20'])}</code></p><p>BNB: <code>{esc(settings['bnb_address'])}</code></p><p>TRON: <code>{esc(settings['tron_address'])}</code></p><p class="muted">Devis Closer ne détient pas les fonds. Le client paie directement le professionnel.</p></div>'''
    return render_template_string(PUBLIC_SIMPLE, title="Payer", heading=f"Payer {q['total']} {q['currency']}", body=f'''{payment_html}<form method="post" enctype="multipart/form-data"><input type="hidden" name="csrf" value="{csrf_token()}"><label>Moyen de paiement<select name="payment_method"><option>MoMo</option><option>USDT TRC20</option><option>USDT BEP20</option><option>BNB</option><option>TRON</option></select></label><label>Identifiant de transaction / TXID<input name="transaction_id"></label><label>Preuve de paiement (image, facultative)<input type="file" name="proof" accept="image/png,image/jpeg,image/webp"></label><button class="btn primary full">Déclarer le paiement</button></form>''')


@app.route("/devis/<int:qid>/paiement", methods=["GET", "POST"])
@login_required
def professional_payment(qid):
    user = current_user()
    q = query("SELECT * FROM quotes WHERE id=%s AND user_id=%s", (qid, user["id"]), one=True)
    if not q: abort(404)
    if request.method == "POST":
        check_csrf()
        commission = (money(q["total"]) * Decimal("0.02")).quantize(Decimal("0.01"))
        execute("INSERT INTO quote_payments(quote_id,professional_id,gross_amount,commission_amount,net_amount,currency,payment_method,status) VALUES(%s,%s,%s,%s,%s,%s,%s,'verified')", (qid,user["id"],q["total"],commission,money(q["total"])-commission,q["currency"],request.form.get("payment_method","Direct")))
        execute("UPDATE quotes SET status='paid' WHERE id=%s", (qid,))
        add_event(qid,"paid","Paiement enregistré par le professionnel",request.remote_addr)
        flash("Paiement enregistré et commission de 2% calculée.", "success")
        return redirect(url_for("devis_detail", qid=qid))
    return html_page("Enregistrer paiement", f'''<section class="formbox"><h1>Paiement — {esc(q['quote_number'])}</h1><p>Montant: <b>{esc(q['total'])} {esc(q['currency'])}</b></p><p>Commission de service 2%: <b>{money(q['total']) * Decimal('0.02')} {esc(q['currency'])}</b></p><form method="post"><input type="hidden" name="csrf" value="{csrf_token()}"><label>Moyen<select name="payment_method"><option>Direct</option><option>MoMo</option><option>Crypto</option><option>Virement</option></select></label><button class="btn primary full">Enregistrer le paiement</button></form></section>''', user)


# ----------------------------
# Payment settings / subscriptions
# ----------------------------

@app.route("/profil/paiements", methods=["GET", "POST"])
@login_required
def payment_settings():
    user = current_user()
    if request.method == "POST":
        check_csrf()
        vals = (request.form.get("momo_operator",""),request.form.get("momo_number",""),request.form.get("momo_name",""),request.form.get("usdt_trc20",""),request.form.get("usdt_bep20",""),request.form.get("bnb_address",""),request.form.get("tron_address",""),user["id"])
        execute("UPDATE payment_settings SET momo_operator=%s,momo_number=%s,momo_name=%s,usdt_trc20=%s,usdt_bep20=%s,bnb_address=%s,tron_address=%s,updated_at=CURRENT_TIMESTAMP WHERE user_id=%s", vals)
        flash("Coordonnées de paiement mises à jour.", "success")
        return redirect(url_for("payment_settings"))
    s = query("SELECT * FROM payment_settings WHERE user_id=%s", (user["id"],), one=True)
    return html_page("Mes paiements", f'''<section class="formbox"><h1>Mes coordonnées de paiement</h1><p>Elles seront affichées au client sur la page de paiement de vos devis.</p><form method="post"><input type="hidden" name="csrf" value="{csrf_token()}"><label>Opérateur MoMo<input name="momo_operator" value="{esc(s['momo_operator'] if s else '')}"></label><label>Numéro MoMo<input name="momo_number" value="{esc(s['momo_number'] if s else '')}"></label><label>Nom du compte<input name="momo_name" value="{esc(s['momo_name'] if s else user['full_name'])}"></label><label>USDT TRC20<input name="usdt_trc20" value="{esc(s['usdt_trc20'] if s else '')}"></label><label>USDT BEP20<input name="usdt_bep20" value="{esc(s['usdt_bep20'] if s else '')}"></label><label>BNB<input name="bnb_address" value="{esc(s['bnb_address'] if s else '')}"></label><label>TRON<input name="tron_address" value="{esc(s['tron_address'] if s else '')}"></label><button class="btn primary full">Enregistrer</button></form></section>''', user)


@app.route("/abonnement")
@login_required
def abonnement():
    user = current_user()
    plan_name, plan = plan_for(user["id"])
    sub = query("SELECT * FROM subscriptions WHERE user_id=%s ORDER BY id DESC LIMIT 1", (user["id"],), one=True)
    cards = ""
    for key, p in PLANS.items():
        if key == "free": continue
        features = ''.join(f'<li>{esc(x)}</li>' for x in p["features"])
        cards += f'<div class="card plan"><h2>{p["name"]}</h2><div class="price">{p["price"]:,.0f} XOF/mois</div><ul>{features}</ul><a class="btn primary" href="/abonnement/{key}/paiement">Payer {p["name"]}</a></div>'
    return html_page("Abonnement", f'''<section><div class="card"><div class="badge">PLAN ACTUEL</div><h1>{plan["name"]}</h1><p>{"Actif jusqu'au " + str(sub["expires_at"]) if sub and sub["expires_at"] else "Plan Free"}</p></div><div class="grid two">{cards}</div></section>''', user)


@app.route("/abonnement/<plan>/paiement", methods=["GET", "POST"])
@login_required
def subscription_payment(plan):
    user = current_user()
    if plan not in ("starter", "pro"): abort(404)
    p = PLANS[plan]
    if request.method == "POST":
        check_csrf()
        method = request.form.get("payment_method", "MoMo")
        txid = request.form.get("transaction_id", "").strip()
        proof = request.files.get("proof")
        data = proof.read() if proof and proof.filename else None
        mime = proof.mimetype if proof and proof.filename else None
        if method == "MoMo" and (not txid or not data):
            flash("Pour MoMo, le transaction ID et la preuve de paiement sont obligatoires.", "danger")
            return redirect(request.url)
        if data and len(data) > 2 * 1024 * 1024: abort(413)
        try:
            pid = execute("INSERT INTO subscription_payments(user_id,plan,amount,currency,payment_method,transaction_id,proof_data,proof_mime,proof_filename,status) VALUES(%s,%s,%s,'XOF',%s,%s,%s,%s,%s,'pending') RETURNING id", (user["id"],plan,p["price"],method,txid or None,data,mime,secure_filename(proof.filename) if proof and proof.filename else None), returning=True)
        except psycopg2.errors.UniqueViolation:
            flash("Cet identifiant de transaction existe déjà.", "danger")
            return redirect(request.url)
        if ADMIN_EMAIL:
            admin = query("SELECT id FROM users WHERE email=%s", (ADMIN_EMAIL,), one=True)
            if admin: notify(admin["id"], "Nouveau paiement abonnement", f"Paiement {pid} de {user['email']} — plan {plan}.")
        flash("Paiement soumis. Il sera vérifié par l'administration.", "success")
        return redirect(url_for("abonnement"))
    return html_page("Paiement abonnement", f'''<section class="formbox wide"><h1>Abonnement {p["name"]}</h1><h2>{p["price"]:,.0f} XOF / mois</h2><p><b>Renouvellement mensuel :</b> cet abonnement est valable 30 jours après validation du paiement.</p><div class="card"><h3>MoMo</h3><p>Nom: <b>{esc(OWNER_NAME)}</b></p><p>Numéro: <b>{esc(OWNER_MOMO)}</b></p><p>International: <b>{esc(OWNER_MOMO_INT)}</b></p></div><div class="card"><h3>Crypto</h3><p>USDT BEP20 / BNB: <code>{esc(OWNER_BSC or 'À configurer')}</code></p><p>USDT TRC20 / TRON: <code>{esc(OWNER_TRON or 'À configurer')}</code></p></div><form method="post" enctype="multipart/form-data"><input type="hidden" name="csrf" value="{csrf_token()}"><label>Moyen de paiement<select name="payment_method"><option>MoMo</option><option>USDT TRC20</option><option>USDT BEP20</option><option>BNB</option><option>TRON</option></select></label><label>Transaction ID / TXID<input name="transaction_id" required></label><label>Capture d'écran / preuve<input type="file" name="proof" accept="image/png,image/jpeg,image/webp" required></label><button class="btn primary full">Soumettre le paiement</button></form></section>''', user)


# ----------------------------
# AI Closer — moteur local sans API externe
# ----------------------------

@app.route("/ai-closer")
@login_required
def ai_closer():
    user = current_user()
    plan_name, _ = plan_for(user["id"])
    if plan_name != "pro":
        return html_page("AI Closer", '<section class="card center"><h1>AI Closer</h1><p>Cette fonctionnalité est réservée au plan Pro.</p><a class="btn primary" href="/abonnement">Passer à Pro</a></section>', user)
    hot = query("SELECT q.*,c.name AS customer_name,c.email,c.phone FROM quotes q LEFT JOIN customers c ON c.id=q.customer_id WHERE q.user_id=%s AND q.status IN ('viewed','negotiation','accepted') ORDER BY CASE WHEN q.status='negotiation' THEN 1 WHEN q.status='viewed' THEN 2 ELSE 3 END,q.updated_at DESC LIMIT 20", (user["id"],))
    cards = ""
    for q in hot:
        if q["status"] == "negotiation": action = "Répondre rapidement aux objections et proposer une version ajustée du devis."
        elif q["status"] == "viewed": action = "Relancer avec une question simple sur le besoin et une prochaine étape claire."
        else: action = "Finaliser la signature et orienter vers le paiement."
        cards += f'<div class="card"><span class="status">{esc(q["status"])}</span><h3>{esc(q["customer_name"])}</h3><p>Devis {esc(q["quote_number"])} — {esc(q["total"])} {esc(q["currency"])}</p><p><b>Prochaine action:</b> {action}</p><a class="btn" href="/devis/{q["id"]}">Ouvrir</a></div>'
    return html_page("AI Closer", f'<section><h1>AI Closer</h1><p>Priorisation locale des prospects et recommandations commerciales.</p><div class="grid three">{cards or "<div class=card>Aucun prospect chaud pour le moment.</div>"}</div></section>', user)


@app.route("/relances")
@login_required
def relances():
    user = current_user()
    quotes = query("SELECT q.*,c.name AS customer_name,c.phone FROM quotes q LEFT JOIN customers c ON c.id=q.customer_id WHERE q.user_id=%s AND q.status IN ('sent','viewed','negotiation') ORDER BY q.updated_at ASC", (user["id"],))
    cards = ""
    for q in quotes:
        msg = f"Bonjour, je reviens vers vous concernant le devis {q['quote_number']}. Avez-vous pu en prendre connaissance ? Je reste disponible pour répondre à vos questions."
        wa = whatsapp_link(q.get("phone"), msg)
        cards += f'<div class="card"><h3>{esc(q["customer_name"])}</h3><p>{esc(q["quote_number"])} — {esc(q["status"])}</p><a class="btn primary" href="{wa}" target="_blank">Relancer sur WhatsApp</a></div>'
    return html_page("Relances", f'<section><h1>Relances</h1><div class="grid three">{cards or "<div class=card>Aucune relance à effectuer.</div>"}</div></section>', user)


# ----------------------------
# Admin
# ----------------------------

@app.route("/admin")
@admin_required
def admin_dashboard():
    users = query("SELECT COUNT(*) AS n FROM users", one=True)["n"]
    active = query("SELECT COUNT(*) AS n FROM subscriptions WHERE status='active' AND plan<>'free'", one=True)["n"]
    pending = query("SELECT COUNT(*) AS n FROM subscription_payments WHERE status='pending'", one=True)["n"]
    commissions = query("SELECT COALESCE(SUM(commission_amount),0) AS n FROM quote_payments WHERE status IN ('pending','verified')", one=True)["n"]
    return html_page("Administration", f'''<section><h1>Administration</h1><div class="stats">{stat("Utilisateurs",users)}{stat("Abonnements payants",active)}{stat("Paiements en attente",pending)}{stat("Commissions",commissions)}</div><div class="grid two"><div class="card"><h2>Paiements abonnements</h2><a class="btn primary" href="/admin/paiements">Vérifier</a></div><div class="card"><h2>Utilisateurs</h2><a class="btn" href="/admin/utilisateurs">Gérer</a></div></div></section>''', current_user())


@app.route("/admin/utilisateurs")
@admin_required
def admin_users():
    rows = query("SELECT id,email,full_name,company_name,role,active,created_at FROM users ORDER BY id DESC LIMIT 200")
    table = "".join(f'<tr><td>{u["id"]}</td><td>{esc(u["email"])}</td><td>{esc(u["full_name"])}</td><td>{esc(u["company_name"])}</td><td>{esc(u["role"])}</td><td>{"Actif" if u["active"] else "Suspendu"}</td><td><form method="post" action="/admin/utilisateur/{u["id"]}/toggle"><input type="hidden" name="csrf" value="{csrf_token()}"><button class="btn">{"Suspendre" if u["active"] else "Réactiver"}</button></form></td></tr>' for u in rows)
    return html_page("Utilisateurs", f'<section><h1>Utilisateurs</h1><div class="card tablewrap"><table><tr><th>ID</th><th>Email</th><th>Nom</th><th>Entreprise</th><th>Rôle</th><th>État</th><th></th></tr>{table}</table></div></section>', current_user())


@app.route("/admin/utilisateur/<int:uid>/toggle", methods=["POST"])
@admin_required
def admin_toggle_user(uid):
    check_csrf()
    if uid == current_user()["id"]: abort(400, description="Vous ne pouvez pas suspendre votre propre compte.")
    execute("UPDATE users SET active=NOT active WHERE id=%s", (uid,))
    execute("INSERT INTO admin_logs(admin_id,action,target_type,target_id) VALUES(%s,'toggle_user','user',%s)", (current_user()["id"],uid))
    return redirect(url_for("admin_users"))


@app.route("/admin/paiements")
@admin_required
def admin_payments():
    rows = query("SELECT p.*,u.email,u.full_name FROM subscription_payments p JOIN users u ON u.id=p.user_id ORDER BY CASE WHEN p.status='pending' THEN 0 ELSE 1 END,p.id DESC LIMIT 200")
    cards = ""
    for p in rows:
        proof = f'<a href="/admin/paiement/{p["id"]}/preuve">Voir preuve</a>' if p["proof_data"] else "Pas de preuve"
        action = ''
        if p["status"] == "pending":
            action = f'<form method="post" action="/admin/paiement/{p["id"]}/valider"><input type="hidden" name="csrf" value="{csrf_token()}"><button class="btn primary">Valider</button></form><form method="post" action="/admin/paiement/{p["id"]}/rejeter"><input type="hidden" name="csrf" value="{csrf_token()}"><input name="reason" placeholder="Motif"><button class="btn danger">Rejeter</button></form>'
        cards += f'<div class="card"><h3>#{p["id"]} — {esc(p["plan"]).upper()}</h3><p>{esc(p["email"])} — {esc(p["full_name"])}</p><p>{esc(p["amount"])} XOF — {esc(p["payment_method"])} — TXID: {esc(p["transaction_id"])}</p><p>Statut: <b>{esc(p["status"])}</b> · {proof}</p><div class="actions">{action}</div></div>'
    return html_page("Paiements", f'<section><h1>Paiements abonnements</h1>{cards or "<div class=card>Aucun paiement.</div>"}</section>', current_user())


@app.route("/admin/paiement/<int:pid>/preuve")
@admin_required
def admin_proof(pid):
    p = query("SELECT proof_data,proof_mime FROM subscription_payments WHERE id=%s", (pid,), one=True)
    if not p or not p["proof_data"]: abort(404)
    return send_file(BytesIO(bytes(p["proof_data"])), mimetype=p["proof_mime"] or "image/jpeg")


@app.route("/admin/paiement/<int:pid>/valider", methods=["POST"])
@admin_required
def admin_validate_payment(pid):
    check_csrf()
    p = query("SELECT * FROM subscription_payments WHERE id=%s", (pid,), one=True)
    if not p: abort(404)
    if p["status"] != "pending": return redirect(url_for("admin_payments"))
    start = now(); expires = start + timedelta(days=30)
    sub = query("SELECT id FROM subscriptions WHERE user_id=%s ORDER BY id DESC LIMIT 1", (p["user_id"],), one=True)
    if sub:
        execute("UPDATE subscriptions SET plan=%s,status='active',started_at=%s,expires_at=%s,payment_id=%s WHERE id=%s", (p["plan"],start,expires,pid,sub["id"]))
    else:
        execute("INSERT INTO subscriptions(user_id,plan,status,started_at,expires_at,payment_id) VALUES(%s,%s,'active',%s,%s,%s)", (p["user_id"],p["plan"],start,expires,pid))
    execute("UPDATE subscription_payments SET status='validated',verified_by=%s,verified_at=CURRENT_TIMESTAMP WHERE id=%s", (current_user()["id"],pid))
    notify(p["user_id"], "Abonnement activé", f"Votre abonnement {p['plan']} est maintenant actif.")
    execute("INSERT INTO admin_logs(admin_id,action,target_type,target_id) VALUES(%s,'validate_payment','subscription_payment',%s)", (current_user()["id"],pid))
    return redirect(url_for("admin_payments"))


@app.route("/admin/paiement/<int:pid>/rejeter", methods=["POST"])
@admin_required
def admin_reject_payment(pid):
    check_csrf()
    reason = request.form.get("reason", "Paiement non validé").strip()
    p = query("SELECT * FROM subscription_payments WHERE id=%s", (pid,), one=True)
    if not p: abort(404)
    execute("UPDATE subscription_payments SET status='rejected',rejection_reason=%s,verified_by=%s,verified_at=CURRENT_TIMESTAMP WHERE id=%s", (reason,current_user()["id"],pid))
    notify(p["user_id"], "Paiement rejeté", reason)
    execute("INSERT INTO admin_logs(admin_id,action,target_type,target_id,details) VALUES(%s,'reject_payment','subscription_payment',%s,%s)", (current_user()["id"],pid,reason))
    return redirect(url_for("admin_payments"))


# ----------------------------
# Notifications
# ----------------------------

@app.route("/notifications")
@login_required
def notifications():
    user = current_user()
    rows = query("SELECT * FROM notifications WHERE user_id=%s ORDER BY id DESC LIMIT 100", (user["id"],))
    execute("UPDATE notifications SET is_read=TRUE WHERE user_id=%s", (user["id"],))
    html = "".join(f'<div class="card"><b>{esc(n["title"])}</b><p>{esc(n["message"])}</p><small>{esc(n["created_at"])}</small></div>' for n in rows)
    return html_page("Notifications", f'<section><h1>Notifications</h1>{html or "<div class=card>Aucune notification.</div>"}</section>', user)


# ----------------------------
# Errors
# ----------------------------

@app.errorhandler(403)
def forbidden(e):
    return html_page("Accès refusé", '<section class="card center"><h1>403</h1><p>Accès refusé.</p></section>', current_user()), 403


@app.errorhandler(404)
def not_found(e):
    return html_page("Introuvable", '<section class="card center"><h1>404</h1><p>Page introuvable.</p></section>', current_user()), 404


@app.errorhandler(413)
def too_large(e):
    return html_page("Fichier trop volumineux", '<section class="card center"><h1>413</h1><p>La preuve dépasse la taille maximale de 2 Mo.</p></section>', current_user()), 413


@app.errorhandler(500)
def server_error(e):
    # Ne jamais interroger PostgreSQL depuis le gestionnaire 500 :
    # si la base est précisément la cause de l'erreur, cela provoquerait
    # une seconde exception et masquerait le vrai problème.
    app.logger.exception("Erreur serveur")
    return html_page("Erreur", '<section class="card center"><h1>Erreur serveur</h1><p>Une erreur interne est survenue. Réessayez dans quelques secondes.</p></section>', None), 500


# ----------------------------
# UI
# ----------------------------

BASE = '''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{ title }} — Devis Closer</title><meta name="description" content="Devis Closer — Transformez vos devis en contrats."><style>
:root{--bg:#080b12;--card:#111722;--line:#273142;--text:#f4f7fb;--muted:#9ba8b8;--blue:#2684ff;--danger:#ff5c68;--ok:#25c78a;--shadow:0 20px 60px rgba(0,0,0,.22)}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 15% 0,#14233b 0,transparent 35%),var(--bg);color:var(--text);font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;line-height:1.55}a{color:#76b4ff;text-decoration:none}a:hover{text-decoration:underline}.nav{position:sticky;top:0;z-index:10;background:rgba(8,11,18,.9);backdrop-filter:blur(14px);border-bottom:1px solid var(--line)}.navin{max-width:1180px;margin:auto;display:flex;align-items:center;gap:14px;padding:14px 18px}.brand{font-weight:900;letter-spacing:-.5px;color:#fff;margin-right:auto}.brand span{color:#4c9aff}.nav a{font-size:14px}.btn{display:inline-flex;align-items:center;justify-content:center;border:1px solid var(--line);background:#151d2a;color:#fff;border-radius:10px;padding:10px 14px;cursor:pointer;text-decoration:none;gap:7px}.btn:hover{background:#1b2636;text-decoration:none}.btn.primary{background:var(--blue);border-color:var(--blue)}.btn.danger{background:transparent;border-color:var(--danger);color:#ff8a92}.full{width:100%}main{max-width:1180px;margin:0 auto;padding:42px 18px 80px}.hero{padding:70px 0;text-align:center;max-width:850px;margin:auto}.hero h1{font-size:clamp(38px,7vw,72px);line-height:1.02;letter-spacing:-3px;margin:16px 0}.hero p{font-size:20px;color:var(--muted)}.badge,.tag{display:inline-block;font-size:11px;font-weight:800;letter-spacing:1.2px;color:#8ec2ff;border:1px solid #28548b;background:#0e2038;border-radius:999px;padding:6px 10px}.tag{color:#9ef0ce;border-color:#24634e;background:#0d2a20;float:right}.actions{display:flex;flex-wrap:wrap;gap:9px;align-items:center}.grid{display:grid;gap:18px}.grid.two{grid-template-columns:repeat(2,minmax(0,1fr))}.grid.three{grid-template-columns:repeat(3,minmax(0,1fr))}.card,.formbox{background:linear-gradient(180deg,rgba(255,255,255,.03),rgba(255,255,255,.015));border:1px solid var(--line);border-radius:16px;padding:22px;box-shadow:var(--shadow)}.formbox{max-width:700px;margin:auto}.formbox.wide{max-width:900px}.center{text-align:center}.prose{max-width:900px;margin:auto}.topline{display:flex;justify-content:space-between;align-items:center;gap:20px;margin-bottom:22px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:20px 0}.stat{padding:18px;border:1px solid var(--line);border-radius:14px;background:#0d131d}.stat small{display:block;color:var(--muted)}.stat strong{font-size:24px;display:block;margin-top:5px}label{display:block;font-weight:700;margin:14px 0}input,select,textarea{width:100%;margin-top:7px;background:#0a1019;border:1px solid #2a3545;color:#fff;border-radius:10px;padding:12px;font:inherit}textarea{min-height:110px;resize:vertical}.check{font-weight:400}.check input{width:auto;margin-right:8px}.price{font-size:30px;font-weight:900;margin:8px 0 15px}.plan.featured{border-color:#3b8fff}.plan ul{min-height:240px;padding-left:20px;color:var(--muted)}li{margin:6px 0}.tablewrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:650px}th,td{padding:12px;border-bottom:1px solid var(--line);text-align:left}.status{display:inline-block;padding:5px 9px;border-radius:999px;background:#182538;color:#9dc8ff;font-size:12px}.totals{max-width:380px;margin:20px 0 0 auto}.itemrow{display:grid;grid-template-columns:1fr 120px 160px 45px;gap:8px;margin:8px 0}.remove{padding:8px}.muted{color:var(--muted)}code{word-break:break-all;color:#b9d7ff}.flash{padding:12px 14px;border-radius:10px;margin-bottom:12px;background:#162234;border:1px solid var(--line)}.flash.success{border-color:#24634e}.flash.danger{border-color:#6b2e35}.flash.warning{border-color:#765e27}footer{border-top:1px solid var(--line);color:var(--muted);padding:25px 18px;text-align:center}@media(max-width:850px){.navin{overflow:auto}.navin>a:not(.brand){white-space:nowrap}.grid.three,.grid.two,.stats{grid-template-columns:1fr}.topline{align-items:flex-start;flex-direction:column}.hero{padding:45px 0}.itemrow{grid-template-columns:1fr 1fr}.itemrow input:first-child{grid-column:1/-1}.itemrow .remove{grid-column:auto}}
</style></head><body><header class="nav"><div class="navin"><a class="brand" href="/">Devis <span>Closer</span></a>{{ nav|safe }}</div></header><main>{% with messages=get_flashed_messages(with_categories=true) %}{% for category,message in messages %}<div class="flash {{ category }}">{{ message }}</div>{% endfor %}{% endwith %}{{ content|safe }}</main><footer>Devis Closer — Transformez vos devis en contrats · <a href="/cgu">CGU</a> · <a href="/health">Statut</a></footer></body></html>'''

PUBLIC = '''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{ title }} — Devis Closer</title><style>body{margin:0;background:#080b12;color:#f5f7fa;font-family:system-ui;padding:20px}.wrap{max-width:850px;margin:auto}.card{background:#111722;border:1px solid #273142;border-radius:16px;padding:22px;margin:16px 0}table{width:100%;border-collapse:collapse}th,td{padding:11px;border-bottom:1px solid #273142;text-align:left}input,textarea,select{width:100%;box-sizing:border-box;background:#0a1019;color:#fff;border:1px solid #2a3545;border-radius:10px;padding:12px;margin:7px 0 14px}.btn{display:inline-block;background:#151d2a;border:1px solid #273142;color:#fff;border-radius:10px;padding:11px 15px;text-decoration:none;cursor:pointer}.primary{background:#2684ff;border-color:#2684ff}.danger{border-color:#ff5c68;background:transparent}.actions{display:flex;gap:9px;flex-wrap:wrap;align-items:center}.brand{font-weight:900}.muted{color:#9ba8b8}.total{font-size:30px;font-weight:900;text-align:right}</style></head><body><div class="wrap"><div class="brand">Devis <span>Closer</span></div><div class="card"><h1>{{ q.quote_number }}</h1><p>{{ q.company_name or q.full_name }}</p><p>Client: {{ q.customer_name or "Client" }}</p><p>{{ q.description or "" }}</p><table><tr><th>Désignation</th><th>Qté</th><th>Prix</th><th>Total</th></tr>{{ rows|safe }}</table><p class="total">{{ q.total }} {{ q.currency }}</p><p class="muted">{{ q.terms or "" }}</p></div>{{ actions|safe }}<div class="card"><p>Ce devis est accessible par lien sécurisé. Vous pouvez demander une modification, accepter, signer et déclarer un paiement.</p><p><a href="/q/{{ q.public_token }}/signer" class="btn primary">Signer le devis</a></p></div></div></body></html>'''

PUBLIC_SIMPLE = '''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{ title }} — Devis Closer</title><style>body{margin:0;background:#080b12;color:#f5f7fa;font-family:system-ui;padding:20px}.wrap{max-width:700px;margin:auto}.card{background:#111722;border:1px solid #273142;border-radius:16px;padding:22px;margin:16px 0}label{display:block;font-weight:700;margin:14px 0}input,textarea,select{width:100%;box-sizing:border-box;background:#0a1019;color:#fff;border:1px solid #2a3545;border-radius:10px;padding:12px;margin-top:7px}.btn{display:inline-block;background:#2684ff;color:#fff;border:0;border-radius:10px;padding:12px 15px;text-decoration:none;cursor:pointer}.full{width:100%}.muted{color:#9ba8b8}</style></head><body><div class="wrap"><div class="card"><h1>{{ heading }}</h1>{{ body|safe }}</div></div></body></html>'''

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
