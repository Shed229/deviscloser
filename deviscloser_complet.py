import os
import re
import secrets
import threading
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO
from urllib.parse import quote as urlquote
from datetime import datetime, timezone, timedelta

import psycopg2
from psycopg2.extras import RealDictCursor

from flask import (
    Flask,
    request,
    redirect,
    session,
    render_template_string,
    abort,
    send_file
)

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


# ============================================================
# DEVIS CLOSER
# Transformez vos devis en contrats
# ============================================================

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "change-me-in-render"
)

app.config["MAX_CONTENT_LENGTH"] = 3 * 1024 * 1024

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = (
    os.environ.get("COOKIE_SECURE", "1") != "0"
)


# ============================================================
# CONFIGURATION
# ============================================================

DATABASE_URL = os.environ.get("DATABASE_URL", "")

ADMIN_EMAIL = os.environ.get(
    "ADMIN_EMAIL",
    ""
).strip().lower()

# Paiement abonnement Devis Closer
MOMO = os.environ.get(
    "MOMO_NUMBER",
    "01 56 85 31 49"
)

MOMO_INT = os.environ.get(
    "MOMO_INTERNATIONAL",
    "2290156853149"
)

MOMO_NAME = os.environ.get(
    "MOMO_NAME",
    "Sosthene Herve EDOH"
)

BSC_ADDR = os.environ.get(
    "BSC_ADDRESS",
    "0xeB3e09b4F53d863dEBb0d49591597741612b6FB1"
)

TRON_ADDR = os.environ.get(
    "TRON_ADDRESS",
    "THwRRQVtymKPwLdXdc7PmQvmvNaugX2cff"
)

APP_NAME = "Devis Closer"

TAGLINE = "Transformez vos devis en contrats"

COMMISSION_RATE = Decimal("0.02")

ALLOWED_IMAGE_EXT = {
    "jpg",
    "jpeg",
    "png",
    "webp"
}

DB_READY = False
DB_LOCK = threading.Lock()


# ============================================================
# PAYS
# ============================================================

COUNTRIES = [
    "Afghanistan",
    "Albanie",
    "Algérie",
    "Allemagne",
    "Andorre",
    "Angola",
    "Antigua-et-Barbuda",
    "Arabie saoudite",
    "Argentine",
    "Arménie",
    "Australie",
    "Autriche",
    "Azerbaïdjan",
    "Bahamas",
    "Bahreïn",
    "Bangladesh",
    "Barbade",
    "Belgique",
    "Belize",
    "Bénin",
    "Bhoutan",
    "Biélorussie",
    "Birmanie",
    "Bolivie",
    "Bosnie-Herzégovine",
    "Botswana",
    "Brésil",
    "Brunei",
    "Bulgarie",
    "Burkina Faso",
    "Burundi",
    "Cabo Verde",
    "Cambodge",
    "Cameroun",
    "Canada",
    "Chili",
    "Chine",
    "Chypre",
    "Colombie",
    "Comores",
    "Congo",
    "Costa Rica",
    "Côte d’Ivoire",
    "Croatie",
    "Cuba",
    "Danemark",
    "Djibouti",
    "Dominique",
    "Égypte",
    "Émirats arabes unis",
    "Équateur",
    "Érythrée",
    "Espagne",
    "Estonie",
    "Eswatini",
    "États-Unis",
    "Éthiopie",
    "Fidji",
    "Finlande",
    "France",
    "Gabon",
    "Gambie",
    "Géorgie",
    "Ghana",
    "Grèce",
    "Grenade",
    "Guatemala",
    "Guinée",
    "Guinée-Bissau",
    "Guinée équatoriale",
    "Guyana",
    "Haïti",
    "Honduras",
    "Hongrie",
    "Inde",
    "Indonésie",
    "Irak",
    "Iran",
    "Irlande",
    "Islande",
    "Israël",
    "Italie",
    "Jamaïque",
    "Japon",
    "Jordanie",
    "Kazakhstan",
    "Kenya",
    "Kirghizistan",
    "Kiribati",
    "Koweït",
    "Laos",
    "Lesotho",
    "Lettonie",
    "Liban",
    "Liberia",
    "Libye",
    "Liechtenstein",
    "Lituanie",
    "Luxembourg",
    "Macédoine du Nord",
    "Madagascar",
    "Malaisie",
    "Malawi",
    "Maldives",
    "Mali",
    "Malte",
    "Maroc",
    "Marshall",
    "Maurice",
    "Mauritanie",
    "Mexique",
    "Micronésie",
    "Moldavie",
    "Monaco",
    "Mongolie",
    "Monténégro",
    "Mozambique",
    "Namibie",
    "Nauru",
    "Népal",
    "Nicaragua",
    "Niger",
    "Nigeria",
    "Norvège",
    "Nouvelle-Zélande",
    "Oman",
    "Ouganda",
    "Ouzbékistan",
    "Pakistan",
    "Palaos",
    "Panama",
    "Papouasie-Nouvelle-Guinée",
    "Paraguay",
    "Pays-Bas",
    "Pérou",
    "Philippines",
    "Pologne",
    "Portugal",
    "Qatar",
    "République centrafricaine",
    "République démocratique du Congo",
    "République dominicaine",
    "Roumanie",
    "Royaume-Uni",
    "Russie",
    "Rwanda",
    "Saint-Christophe-et-Niévès",
    "Sainte-Lucie",
    "Saint-Marin",
    "Saint-Vincent-et-les-Grenadines",
    "Salomon",
    "Salvador",
    "Samoa",
    "Sao Tomé-et-Principe",
    "Sénégal",
    "Serbie",
    "Seychelles",
    "Sierra Leone",
    "Singapour",
    "Slovaquie",
    "Slovénie",
    "Somalie",
    "Soudan",
    "Soudan du Sud",
    "Sri Lanka",
    "Suède",
    "Suisse",
    "Suriname",
    "Syrie",
    "Tadjikistan",
    "Tanzanie",
    "Tchad",
    "Thaïlande",
    "Timor oriental",
    "Togo",
    "Tonga",
    "Trinité-et-Tobago",
    "Tunisie",
    "Turkménistan",
    "Tuvalu",
    "Turquie",
    "Ukraine",
    "Uruguay",
    "Vanuatu",
    "Vatican",
    "Venezuela",
    "Viêt Nam",
    "Yémen",
    "Zambie",
    "Zimbabwe"
]


# ============================================================
# PLANS
# ============================================================

PLANS = {
    "free": {
        "name": "Free",
        "price": Decimal("0"),
        "quotes": 1,
        "clients": 5,
        "users": 1
    },

    "starter": {
        "name": "Starter",
        "price": Decimal("6500"),
        "quotes": 50,
        "clients": 100,
        "users": 2
    },

    "pro": {
        "name": "Pro",
        "price": Decimal("15000"),
        "quotes": None,
        "clients": None,
        "users": 5
    }
}


# ============================================================
# BASE DE DONNÉES
# ============================================================

def db_connect():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL n'est pas configurée."
        )

    url = DATABASE_URL

    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    return psycopg2.connect(
        url,
        sslmode=os.environ.get(
            "DB_SSLMODE",
            "require"
        )
    )


def db_execute(
    sql,
    params=(),
    fetchone=False,
    fetchall=False,
    commit=False
):
    conn = db_connect()

    try:
        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(sql, params)

            if fetchone:
                data = cur.fetchone()

            elif fetchall:
                data = cur.fetchall()

            else:
                data = None

        if commit:
            conn.commit()

        return data

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def ensure_free_subscriptions(conn):
    with conn.cursor() as cur:

        cur.execute(
            "SELECT id FROM users WHERE active=TRUE"
        )

        ids = [
            row[0]
            for row in cur.fetchall()
        ]

        for user_id in ids:

            cur.execute(
                """
                SELECT id
                FROM subscriptions
                WHERE user_id=%s
                AND status='active'
                LIMIT 1
                """,
                (user_id,)
            )

            if not cur.fetchone():

                cur.execute(
                    """
                    INSERT INTO subscriptions
                    (user_id, plan_code, status)
                    VALUES (%s, 'free', 'active')
                    """,
                    (user_id,)
                )

    conn.commit()


def init_db():

    statements = [

        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name VARCHAR(200) NOT NULL,
            role VARCHAR(30) NOT NULL DEFAULT 'user',
            company_name VARCHAR(255),
            phone VARCHAR(80),
            address TEXT,
            country VARCHAR(120) DEFAULT 'Bénin',
            currency VARCHAR(10) DEFAULT 'XOF',
            language VARCHAR(10) DEFAULT 'fr',

            momo_number VARCHAR(100),
            momo_name VARCHAR(200),

            usdt_trc20 VARCHAR(120),
            usdt_bep20 VARCHAR(120),
            bnb_address VARCHAR(120),
            tron_address VARCHAR(120),

            cgu_accepted BOOLEAN NOT NULL DEFAULT FALSE,
            cgu_version VARCHAR(30),
            cgu_accepted_at TIMESTAMPTZ,

            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            active BOOLEAN NOT NULL DEFAULT TRUE
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS customers (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL
                REFERENCES users(id)
                ON DELETE CASCADE,

            name VARCHAR(255) NOT NULL,
            company VARCHAR(255),
            email VARCHAR(255),
            phone VARCHAR(100),
            address TEXT,
            country VARCHAR(120),
            notes TEXT,

            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS quotes (
            id SERIAL PRIMARY KEY,

            user_id INTEGER NOT NULL
                REFERENCES users(id)
                ON DELETE CASCADE,

            customer_id INTEGER
                REFERENCES customers(id)
                ON DELETE SET NULL,

            quote_number VARCHAR(60) UNIQUE NOT NULL,
            public_token VARCHAR(180) UNIQUE NOT NULL,

            status VARCHAR(30) NOT NULL DEFAULT 'draft',

            currency VARCHAR(10) NOT NULL DEFAULT 'XOF',

            discount NUMERIC(14,2) NOT NULL DEFAULT 0,
            tax_rate NUMERIC(6,3) NOT NULL DEFAULT 0,

            terms TEXT,

            issue_date DATE NOT NULL DEFAULT CURRENT_DATE,
            expires_at DATE,

            viewed_at TIMESTAMPTZ,
            accepted_at TIMESTAMPTZ,
            refused_at TIMESTAMPTZ,
            signed_at TIMESTAMPTZ,
            paid_at TIMESTAMPTZ,

            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS quote_items (
            id SERIAL PRIMARY KEY,

            quote_id INTEGER NOT NULL
                REFERENCES quotes(id)
                ON DELETE CASCADE,

            description TEXT NOT NULL,

            quantity NUMERIC(12,2)
                NOT NULL DEFAULT 1,

            unit_price NUMERIC(14,2)
                NOT NULL DEFAULT 0
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS quote_events (
            id SERIAL PRIMARY KEY,

            quote_id INTEGER NOT NULL
                REFERENCES quotes(id)
                ON DELETE CASCADE,

            event_type VARCHAR(50) NOT NULL,
            note TEXT,
            ip_address VARCHAR(100),

            created_at TIMESTAMPTZ
                NOT NULL DEFAULT NOW()
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS signatures (
            id SERIAL PRIMARY KEY,

            quote_id INTEGER UNIQUE NOT NULL
                REFERENCES quotes(id)
                ON DELETE CASCADE,

            signer_name VARCHAR(255) NOT NULL,
            signer_email VARCHAR(255),

            ip_address VARCHAR(100),

            signed_at TIMESTAMPTZ
                NOT NULL DEFAULT NOW()
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS subscription_payments (
            id SERIAL PRIMARY KEY,

            user_id INTEGER NOT NULL
                REFERENCES users(id)
                ON DELETE CASCADE,

            plan_code VARCHAR(30) NOT NULL,

            amount NUMERIC(14,2) NOT NULL,

            currency VARCHAR(10)
                NOT NULL DEFAULT 'XOF',

            method VARCHAR(50) NOT NULL,

            transaction_id VARCHAR(255)
                UNIQUE NOT NULL,

            proof_data BYTEA,
            proof_mime VARCHAR(100),
            proof_filename VARCHAR(255),

            status VARCHAR(30)
                NOT NULL DEFAULT 'pending',

            rejection_reason TEXT,

            created_at TIMESTAMPTZ
                NOT NULL DEFAULT NOW(),

            verified_at TIMESTAMPTZ,

            verified_by INTEGER
                REFERENCES users(id)
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS subscriptions (
            id SERIAL PRIMARY KEY,

            user_id INTEGER NOT NULL
                REFERENCES users(id)
                ON DELETE CASCADE,

            plan_code VARCHAR(30)
                NOT NULL DEFAULT 'free',

            status VARCHAR(30)
                NOT NULL DEFAULT 'active',

            started_at TIMESTAMPTZ
                NOT NULL DEFAULT NOW(),

            expires_at TIMESTAMPTZ,

            payment_id INTEGER
                REFERENCES subscription_payments(id)
                ON DELETE SET NULL
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS quote_payments (
            id SERIAL PRIMARY KEY,

            quote_id INTEGER UNIQUE NOT NULL
                REFERENCES quotes(id)
                ON DELETE CASCADE,

            professional_user_id INTEGER NOT NULL
                REFERENCES users(id)
                ON DELETE CASCADE,

            gross_amount NUMERIC(14,2) NOT NULL,

            commission_amount NUMERIC(14,2) NOT NULL,

            net_amount NUMERIC(14,2) NOT NULL,

            currency VARCHAR(10) NOT NULL,

            method VARCHAR(50) NOT NULL,

            transaction_id VARCHAR(255)
                UNIQUE NOT NULL,

            proof_data BYTEA,
            proof_mime VARCHAR(100),
            proof_filename VARCHAR(255),

            payer_name VARCHAR(255),

            status VARCHAR(30)
                NOT NULL DEFAULT 'pending',

            created_at TIMESTAMPTZ
                NOT NULL DEFAULT NOW(),

            verified_at TIMESTAMPTZ,

            verified_by INTEGER
                REFERENCES users(id)
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS notifications (
            id SERIAL PRIMARY KEY,

            user_id INTEGER NOT NULL
                REFERENCES users(id)
                ON DELETE CASCADE,

            title VARCHAR(255) NOT NULL,

            message TEXT NOT NULL,

            read_at TIMESTAMPTZ,

            created_at TIMESTAMPTZ
                NOT NULL DEFAULT NOW()
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS admin_logs (
            id SERIAL PRIMARY KEY,

            admin_id INTEGER
                REFERENCES users(id)
                ON DELETE SET NULL,

            action VARCHAR(100) NOT NULL,

            details TEXT,

            created_at TIMESTAMPTZ
                NOT NULL DEFAULT NOW()
        )
        """
    ]

    conn = db_connect()

    try:

        with conn.cursor() as cur:

            for statement in statements:
                cur.execute(statement)

        conn.commit()

        ensure_free_subscriptions(conn)

    finally:
        conn.close()


# ============================================================
# CSRF
# ============================================================

def csrf_token():

    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)

    return session["csrf"]


def csrf_field():

    return (
        '<input type="hidden" '
        'name="csrf_token" value="'
        + csrf_token()
        + '">'
    )


def check_csrf():

    submitted = request.form.get(
        "csrf_token",
        ""
    )

    stored = session.get(
        "csrf",
        ""
    )

    if not submitted or not stored:

        abort(
            400,
            "Jeton CSRF invalide."
        )

    if not secrets.compare_digest(
        submitted,
        stored
    ):

        abort(
            400,
            "Jeton CSRF invalide."
        )


# ============================================================
# UTILITAIRES
# ============================================================

def esc(value):

    if value is None:
        return ""

    text = str(value)

    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def money(value):

    try:

        number = Decimal(
            str(value or 0)
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        return (
            f"{number:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", " ")
        )

    except Exception:

        return "0,00"


def now_utc():

    return datetime.now(
        timezone.utc
    )


def allowed_image(file):

    if not file or not file.filename:
        return False

    if "." not in file.filename:
        return False

    extension = (
        file.filename
        .rsplit(".", 1)[-1]
        .lower()
    )

    return extension in ALLOWED_IMAGE_EXT


# ============================================================
# CSS
# ============================================================

CSS = """
:root{
    --bg:#080a12;
    --card:#111522;
    --card2:#171c2b;
    --text:#f6f8ff;
    --muted:#9da7bb;
    --blue:#4da3ff;
    --green:#42d392;
    --red:#ff6878;
    --line:#273047;
    --gold:#f4c95d;
}

*{
    box-sizing:border-box;
}

body{
    margin:0;
    background:
        radial-gradient(
            circle at top,
            #121a31 0,
            #080a12 45%
        );
    color:var(--text);
    font-family:
        Arial,
        Helvetica,
        sans-serif;
    line-height:1.5;
}

a{
    color:var(--blue);
    text-decoration:none;
}

header{
    position:sticky;
    top:0;
    z-index:10;
    background:rgba(8,10,18,.94);
    backdrop-filter:blur(10px);
    border-bottom:1px solid var(--line);
    padding:14px 5%;
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:18px;
}

.brand a{
    font-size:22px;
    font-weight:800;
    color:#fff;
}

.brand span{
    color:var(--blue);
}

nav{
    display:flex;
    gap:12px;
    flex-wrap:wrap;
    justify-content:flex-end;
}

nav a{
    color:#dbe3f5;
    font-size:14px;
}

main{
    max-width:1180px;
    margin:0 auto;
    padding:34px 18px 70px;
}

.hero{
    text-align:center;
    padding:45px 15px;
}

.hero h1{
    font-size:
        clamp(34px,7vw,64px);
    line-height:1.05;
    margin:
        0 0 14px;
}

.hero h1 span{
    color:var(--blue);
}

.hero p{
    color:var(--muted);
    font-size:18px;
    max-width:720px;
    margin:
        0 auto 26px;
}

.btn{
    display:inline-block;
    border:0;
    border-radius:10px;
    padding:12px 18px;
    background:var(--blue);
    color:#06101d;
    font-weight:800;
    cursor:pointer;
}

.btn.secondary{
    background:#20283a;
    color:#fff;
}

.btn.green{
    background:var(--green);
    color:#06130d;
}

.btn.red{
    background:var(--red);
    color:#21060a;
}

.btn.gold{
    background:var(--gold);
    color:#171004;
}

.grid{
    display:grid;
    grid-template-columns:
        repeat(
            auto-fit,
            minmax(250px,1fr)
        );
    gap:18px;
}

.card{
    background:
        linear-gradient(
            180deg,
            var(--card),
            #0d111d
        );
    border:1px solid var(--line);
    border-radius:16px;
    padding:20px;
    box-shadow:
        0 8px 30px #0005;
}

.card h2,
.card h3{
    margin-top:0;
}

.muted{
    color:var(--muted);
}

.price{
    font-size:32px;
    font-weight:900;
    margin:10px 0;
}

.popular{
    border-color:var(--blue);
    box-shadow:
        0 0 30px #4da3ff18;
}

.tag{
    display:inline-block;
    background:#26344d;
    color:#cfe5ff;
    border-radius:999px;
    padding:4px 9px;
    font-size:12px;
}

.form{
    max-width:720px;
    margin:0 auto;
}

.field{
    margin-bottom:14px;
}

.field label{
    display:block;
    margin-bottom:6px;
    font-weight:700;
}

.field input,
.field select,
.field textarea{
    width:100%;
    padding:12px;
    border-radius:9px;
    border:1px solid var(--line);
    background:#0b0f19;
    color:#fff;
    outline:none;
}

.field textarea{
    min-height:100px;
    resize:vertical;
}

.row{
    display:grid;
    grid-template-columns:
        repeat(2,1fr);
    gap:14px;
}

.tablewrap{
    overflow:auto;
}

.table{
    width:100%;
    border-collapse:collapse;
}

.table th,
.table td{
    padding:11px;
    border-bottom:1px solid var(--line);
    text-align:left;
    white-space:nowrap;
}

.status{
    font-weight:800;
}

.status.sent,
.status.viewed,
.status.negotiation{
    color:var(--gold);
}

.status.accepted,
.status.signed,
.status.paid{
    color:var(--green);
}

.status.refused,
.status.expired{
    color:var(--red);
}

.notice{
    padding:13px 15px;
    border:1px solid var(--line);
    background:#111827;
    border-radius:10px;
    margin:12px 0;
}

.success{
    border-color:#2c8d68;
}

.danger{
    border-color:#8f3845;
}

.stats{
    display:grid;
    grid-template-columns:
        repeat(
            auto-fit,
            minmax(150px,1fr)
        );
    gap:12px;
}

.stat{
    background:var(--card);
    border:1px solid var(--line);
    border-radius:13px;
    padding:16px;
}

.stat b{
    font-size:25px;
    display:block;
}

.quote-paper{
    background:#fff;
    color:#10131a;
    border-radius:12px;
    padding:28px;
    max-width:850px;
    margin:auto;
}

.quote-paper table{
    width:100%;
    border-collapse:collapse;
}

.quote-paper th,
.quote-paper td{
    padding:9px;
    border-bottom:1px solid #ddd;
    text-align:left;
}

.quote-paper .total{
    text-align:right;
    font-size:22px;
    font-weight:800;
}

.actions{
    display:flex;
    gap:9px;
    flex-wrap:wrap;
    margin:15px 0;
}

.small{
    font-size:13px;
}

.check{
    display:flex;
    gap:8px;
    align-items:flex-start;
}

.check input{
    margin-top:5px;
}

footer{
    border-top:1px solid var(--line);
    padding:25px 5%;
    text-align:center;
    color:var(--muted);
    font-size:13px;
}

@media(max-width:700px){

    header{
        align-items:flex-start;
        flex-direction:column;
    }

    nav{
        justify-content:flex-start;
    }

    .row{
        grid-template-columns:1fr;
    }

    .hero{
        padding-top:25px;
    }

    .table th,
    .table td{
        font-size:13px;
    }
}
"""


# ============================================================
# AUTHENTIFICATION
# ============================================================

def current_user():

    user_id = session.get(
        "user_id"
    )

    if not user_id:
        return None

    return db_execute(
        """
        SELECT *
        FROM users
        WHERE id=%s
        AND active=TRUE
        """,
        (user_id,),
        fetchone=True
    )


def login_required():

    user = current_user()

    if not user:

        return (
            None,
            redirect(
                "/connexion?next="
                + urlquote(request.path)
            )
        )

    return user, None


def admin_required():

    user = current_user()

    if not user:
        abort(403)

    if user["role"] != "admin":
        abort(403)

    return user


# ============================================================
# LAYOUT
# ============================================================

def layout(title, body):

    user = current_user()

    nav = (
        '<a href="/">Accueil</a>'
        '<a href="/tarifs">Tarifs</a>'
    )

    if user:

        nav += (
            '<a href="/dashboard">Dashboard</a>'
            '<a href="/clients">Clients</a>'
            '<a href="/nouveau-devis">Nouveau devis</a>'
            '<a href="/profil">Profil</a>'
        )

        if user["role"] == "admin":
            nav += '<a href="/admin">Admin</a>'

        nav += (
            '<a href="/deconnexion">'
            'Déconnexion'
            '</a>'
        )

    else:

        nav += (
            '<a href="/connexion">'
            'Connexion'
            '</a>'
            '<a href="/inscription">'
            'Inscription'
            '</a>'
        )

    html = ''.join([
        '<!doctype html>',
        '<html lang="fr">',
        '<head>',
        '<meta charset="utf-8">',
        '<meta name="viewport" ',
        'content="width=device-width,initial-scale=1">',
        '<meta name="description" ',
        'content="Devis Closer - Transformez vos devis en contrats">',
        '<title>',
        esc(title),
        ' — ',
        APP_NAME,
        '</title>',
        '<style>',
        CSS,
        '</style>',
        '</head>',
        '<body>',

        '<header>',

        '<div class="brand">',
        '<a href="/">',
        'Devis <span>Closer</span>',
        '</a>',
        '</div>',

        '<nav>',
        nav,
        '</nav>',

        '</header>',

        '<main>',
        body,
        '</main>',

        '<footer>',
        '<strong>Devis Closer</strong>',
        ' — ',
        TAGLINE,
        '<br>',
        '<a href="/cgu">CGU</a>',
        ' · Paiements directs au professionnel',
        ' · Commission de service : 2%',
        '</footer>',

        '</body>',
        '</html>'
    ])

    return render_template_string(html)


# ============================================================
# ABONNEMENT
# ============================================================

def get_plan(user_id):

    row = db_execute(
        """
        SELECT *
        FROM subscriptions
        WHERE user_id=%s
        AND status='active'
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,),
        fetchone=True
    )

    if not row:
        return "free", PLANS["free"]

    code = row["plan_code"]

    if code not in PLANS:
        code = "free"

    if (
        row["expires_at"]
        and row["expires_at"] < now_utc()
    ):

        db_execute(
            """
            UPDATE subscriptions
            SET status='expired'
            WHERE id=%s
            """,
            (row["id"],),
            commit=True
        )

        return "free", PLANS["free"]

    return code, PLANS[code]


def quote_count_this_month(user_id):

    row = db_execute(
        """
        SELECT COUNT(*) AS n
        FROM quotes
        WHERE user_id=%s
        AND date_trunc(
            'month',
            created_at
        ) =
        date_trunc(
            'month',
            CURRENT_DATE::timestamp
        )
        """,
        (user_id,),
        fetchone=True
    )

    return int(row["n"])


def client_count(user_id):

    row = db_execute(
        """
        SELECT COUNT(*) AS n
        FROM customers
        WHERE user_id=%s
        """,
        (user_id,),
        fetchone=True
    )

    return int(row["n"])


def can_create_quote(user_id):

    code, plan = get_plan(
        user_id
    )

    limit = plan["quotes"]

    allowed = (
        limit is None
        or quote_count_this_month(user_id) < limit
    )

    return allowed, code, limit


# ============================================================
# QUOTES
# ============================================================

def add_event(
    quote_id,
    event_type,
    note=""
):

    db_execute(
        """
        INSERT INTO quote_events
        (
            quote_id,
            event_type,
            note,
            ip_address
        )
        VALUES (%s,%s,%s,%s)
        """,
        (
            quote_id,
            event_type,
            note,
            request.headers.get(
                "X-Forwarded-For",
                request.remote_addr
            )
        ),
        commit=True
    )


def notify(
    user_id,
    title,
    message
):

    db_execute(
        """
        INSERT INTO notifications
        (user_id,title,message)
        VALUES (%s,%s,%s)
        """,
        (
            user_id,
            title,
            message
        ),
        commit=True
    )


def quote_totals(quote_id):

    rows = db_execute(
        """
        SELECT quantity,unit_price
        FROM quote_items
        WHERE quote_id=%s
        """,
        (quote_id,),
        fetchall=True
    )

    subtotal = sum(
        (
            Decimal(str(r["quantity"]))
            *
            Decimal(str(r["unit_price"]))
            for r in rows
        ),
        Decimal("0")
    )

    quote = db_execute(
        """
        SELECT discount,tax_rate
        FROM quotes
        WHERE id=%s
        """,
        (quote_id,),
        fetchone=True
    )

    discount = Decimal(
        str(
            quote["discount"]
            or 0
        )
    )

    base = max(
        Decimal("0"),
        subtotal - discount
    )

    tax = (
        base
        *
        Decimal(
            str(
                quote["tax_rate"]
                or 0
            )
        )
        /
        Decimal("100")
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    total = base + tax

    return (
        subtotal,
        discount,
        tax,
        total
    )


def quote_access(
    quote_id,
    user_id
):

    quote = db_execute(
        """
        SELECT *
        FROM quotes
        WHERE id=%s
        AND user_id=%s
        """,
        (
            quote_id,
            user_id
        ),
        fetchone=True
    )

    if not quote:
        abort(404)

    return quote


# ============================================================
# INITIALISATION DB
# ============================================================

@app.before_request
def startup():

    global DB_READY

    if request.endpoint == "static":
        return

    if DB_READY:
        return

    with DB_LOCK:

        if DB_READY:
            return

        try:

            init_db()

            DB_READY = True

        except Exception as exc:

            app.logger.error(
                "Database initialization error: %s",
                exc
            )

            if request.path == "/health":
                return (
                    "DB ERROR",
                    503
                )


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health():

    try:

        db_execute(
            "SELECT 1"
        )

        return (
            "OK - Devis Closer - "
            "PostgreSQL",
            200
        )

    except Exception as exc:

        return (
            "ERROR - "
            + str(exc)[:120],
            503
        )


# ============================================================
# ACCUEIL
# ============================================================

@app.route("/")
def home():

    body = ''.join([

        '<section class="hero">',

        '<div class="tag">',
        'SaaS commercial',
        '</div>',

        '<h1>',
        'Transformez vos devis en ',
        '<span>contrats</span>.',
        '</h1>',

        '<p>',
        'Devis Closer vous aide à créer, envoyer, ',
        'suivre, relancer, négocier, signer et ',
        'enregistrer le paiement de vos devis.',
        '</p>',

        '<div class="actions" ',
        'style="justify-content:center">',

        '<a class="btn" href="/inscription">',
        'Commencer gratuitement',
        '</a>',

        '<a class="btn secondary" href="/tarifs">',
        'Voir les tarifs',
        '</a>',

        '</div>',

        '</section>',

        '<div class="grid">',

        '<div class="card">',
        '<h3>Créer & envoyer</h3>',
        '<p class="muted">',
        'Créez des devis professionnels et ',
        'partagez-les par WhatsApp avec un ',
        'lien sécurisé.',
        '</p>',
        '</div>',

        '<div class="card">',
        '<h3>Suivre & relancer</h3>',
        '<p class="muted">',
        'Voyez quand un devis est consulté ',
        'et utilisez les relances pour accélérer ',
        'la décision.',
        '</p>',
        '</div>',

        '<div class="card">',
        '<h3>Signer & payer</h3>',
        '<p class="muted">',
        'Le client peut accepter, signer et ',
        'déclarer son paiement depuis le devis public.',
        '</p>',
        '</div>',

        '<div class="card">',
        '<h3>Closer</h3>',
        '<p class="muted">',
        'Le module Closer fournit des suggestions ',
        'commerciales à partir du comportement ',
        'du prospect.',
        '</p>',
        '</div>',

        '</div>'
    ])

    return layout(
        "Accueil",
        body
    )


# ============================================================
# TARIFS
# ============================================================

@app.route("/tarifs")
def tarifs():

    descriptions = {

        "free": [
            "1 devis/mois",
            "5 clients",
            "WhatsApp + email",
            "Lien public",
            "Suivi basique",
            "1 modèle",
            "Dashboard basique"
        ],

        "starter": [
            "50 devis/mois",
            "100 clients",
            "WhatsApp + email",
            "Suivi & relances",
            "5 modèles",
            "Signature électronique",
            "Paiements de devis",
            "Statistiques",
            "2 utilisateurs"
        ],

        "pro": [
            "Devis illimités",
            "Clients illimités",
            "Relances automatiques",
            "Modèles illimités",
            "Signature électronique",
            "Paiements de devis",
            "Statistiques avancées",
            "Historique complet",
            "AI Closer",
            "Prospects chauds",
            "Aide à la négociation",
            "5 utilisateurs",
            "Support prioritaire"
        ]
    }

    cards = []

    for code in [
        "free",
        "starter",
        "pro"
    ]:

        plan = PLANS[code]

        items = ''.join(
            '<li>' + esc(item) + '</li>'
            for item in descriptions[code]
        )

        if code == "free":
            price = "0 XOF"
        else:
            price = (
                money(plan["price"])
                + " XOF/mois"
            )

        card = ''.join([

            '<div class="card ',
            'popular' if code == "pro" else '',
            '">',

            '<span class="tag">'
            if code == "pro"
            else '',

            'POPULAIRE'
            if code == "pro"
            else '',

            '</span>'
            if code == "pro"
            else '',

            '<h2>',
            esc(plan["name"]),
            '</h2>',

            '<div class="price">',
            price,
            '</div>',

            '<ul>',
            items,
            '</ul>',

            '<a class="btn" href="/inscription">',
            'Créer un compte',
            '</a>',

            '</div>'
        ])

        cards.append(card)

    body = ''.join([

        '<h1>Des plans simples</h1>',

        '<p class="muted">',
        'Choisissez le niveau adapté à votre activité.',
        '</p>',

        '<div class="grid">',
        ''.join(cards),
        '</div>'
    ])

    return layout(
        "Tarifs",
        body
    )


# ============================================================
# INSCRIPTION
# ============================================================

@app.route(
    "/inscription",
    methods=["GET", "POST"]
)
def inscription():

    if request.method == "POST":

        check_csrf()

        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        company = request.form.get(
            "company_name",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        country = request.form.get(
            "country",
            "Bénin"
        ).strip()

        currency = request.form.get(
            "currency",
            "XOF"
        ).strip().upper()

        cgu = (
            request.form.get("cgu")
            == "on"
        )

        valid_email = re.match(
            r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
            email
        )

        if (
            len(full_name) < 2
            or not valid_email
            or len(password) < 8
            or not cgu
        ):

            return layout(
                "Inscription",
                '<div class="notice danger">'
                'Vérifiez les champs. '
                'Mot de passe : 8 caractères minimum. '
                'L’acceptation des CGU est obligatoire.'
                '</div>'
                +
                signup_form(
                    full_name,
                    email,
                    company,
                    phone,
                    country,
                    currency
                )
            )

        exists = db_execute(
            """
            SELECT id
            FROM users
            WHERE email=%s
            """,
            (email,),
            fetchone=True
        )

        if exists:

            return layout(
                "Inscription",
                '<div class="notice danger">'
                'Cette adresse email est déjà utilisée.'
                '</div>'
                +
                signup_form(
                    full_name,
                    email,
                    company,
                    phone,
                    country,
                    currency
                )
            )

        count = db_execute(
            """
            SELECT COUNT(*) AS n
            FROM users
            """,
            fetchone=True
        )["n"]

        role = "user"

        if (
            ADMIN_EMAIL
            and email == ADMIN_EMAIL
        ):
            role = "admin"

        elif int(count) == 0:
            role = "admin"

        conn = db_connect()

        try:

            with conn.cursor(
                cursor_factory=RealDictCursor
            ) as cur:

                cur.execute(
                    """
                    INSERT INTO users
                    (
                        email,
                        password_hash,
                        full_name,
                        role,
                        company_name,
                        phone,
                        country,
                        currency,
                        cgu_accepted,
                        cgu_version,
                        cgu_accepted_at
                    )
                    VALUES
                    (
                        %s,%s,%s,%s,%s,%s,%s,%s,
                        TRUE,'1.0',NOW()
                    )
                    RETURNING id
                    """,
                    (
                        email,
                        generate_password_hash(
                            password
                        ),
                        full_name,
                        role,
                        company,
                        phone,
                        country,
                        currency
                    )
                )

                user_id = cur.fetchone()["id"]

                cur.execute(
                    """
                    INSERT INTO subscriptions
                    (
                        user_id,
                        plan_code,
                        status
                    )
                    VALUES
                    (%s,'free','active')
                    """,
                    (user_id,)
                )

            conn.commit()

        finally:
            conn.close()

        session.clear()

        session["user_id"] = user_id

        csrf_token()

        return redirect(
            "/dashboard"
        )

    return layout(
        "Inscription",
        signup_form()
    )


def signup_form(
    full_name="",
    email="",
    company="",
    phone="",
    country="Bénin",
    currency="XOF"
):

    country_options = ''.join(
        '<option value="'
        + esc(country_name)
        + '">'
        for country_name
        in COUNTRIES
    )

    return ''.join([

        '<form class="form card" method="post">',

        csrf_field(),

        '<h1>Créer votre compte</h1>',

        '<p class="muted">',
        'Votre compte démarre avec le plan Free.',
        '</p>',

        '<div class="field">',
        '<label>Nom complet *</label>',
        '<input name="full_name" required value="',
        esc(full_name),
        '">',
        '</div>',

        '<div class="field">',
        '<label>Email *</label>',
        '<input type="email" name="email" ',
        'required value="',
        esc(email),
        '">',
        '</div>',

        '<div class="field">',
        '<label>Mot de passe *</label>',
        '<input type="password" ',
        'name="password" ',
        'required minlength="8">',
        '</div>',

        '<div class="row">',

        '<div class="field">',
        '<label>Entreprise</label>',
        '<input name="company_name" value="',
        esc(company),
        '">',
        '</div>',

        '<div class="field">',
        '<label>Téléphone</label>',
        '<input name="phone" value="',
        esc(phone),
        '">',
        '</div>',

        '</div>',

        '<div class="row">',

        '<div class="field">',

        '<label>Pays</label>',

        '<input list="country-list" ',
        'name="country" ',
        'value="',
        esc(country),
        '" required>',

        '<datalist id="country-list">',
        country_options,
        '</datalist>',

        '</div>',

        '<div class="field">',
        '<label>Devise</label>',
        '<input name="currency" ',
        'value="',
        esc(currency),
        '" maxlength="10">',
        '</div>',

        '</div>',

        '<label class="check">',

        '<input type="checkbox" ',
        'name="cgu" required>',

        '<span>',
        'J’ai lu et j’accepte les ',
        '<a href="/cgu" target="_blank">',
        'Conditions Générales d’Utilisation',
        '</a>.',
        '</span>',

        '</label>',

        '<br>',

        '<button class="btn" type="submit">',
        'Créer mon compte',
        '</button>',

        '</form>'
    ])


# ============================================================
# CONNEXION
# ============================================================

@app.route(
    "/connexion",
    methods=["GET", "POST"]
)
def connexion():

    if request.method == "POST":

        check_csrf()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        user = db_execute(
            """
            SELECT *
            FROM users
            WHERE email=%s
            AND active=TRUE
            """,
            (email,),
            fetchone=True
        )

        if (
            not user
            or not check_password_hash(
                user["password_hash"],
                password
            )
        ):

            return layout(
                "Connexion",
                '<div class="notice danger">'
                'Email ou mot de passe incorrect.'
                '</div>'
                +
                login_form(email)
            )

        session.clear()

        session["user_id"] = user["id"]

        csrf_token()

        return redirect(
            request.args.get("next")
            or "/dashboard"
        )

    return layout(
        "Connexion",
        login_form()
    )


def login_form(email=""):

    return ''.join([

        '<form class="form card" method="post">',

        csrf_field(),

        '<h1>Connexion</h1>',

        '<div class="field">',
        '<label>Email</label>',
        '<input type="email" name="email" ',
        'required value="',
        esc(email),
        '">',
        '</div>',

        '<div class="field">',
        '<label>Mot de passe</label>',
        '<input type="password" ',
        'name="password" required>',
        '</div>',

        '<button class="btn" type="submit">',
        'Se connecter',
        '</button>',

        '</form>'
    ])


# ============================================================
# DECONNEXION
# ============================================================

@app.route("/deconnexion")
def deconnexion():

    session.clear()

    return redirect("/")


# ============================================================
# CGU
# ============================================================

@app.route("/cgu")
def cgu():

    body = ''.join([

        '<div class="card">',

        '<h1>',
        'Conditions Générales d’Utilisation',
        '</h1>',

        '<p><strong>Version 1.0</strong></p>',

        '<h3>1. Objet</h3>',

        '<p>',
        'Devis Closer fournit un logiciel permettant ',
        'de créer, transmettre, suivre, relancer, ',
        'négocier, accepter, signer et enregistrer ',
        'le paiement de devis.',
        '</p>',

        '<h3>2. Responsabilité de l’utilisateur</h3>',

        '<p>',
        'L’utilisateur reste responsable de ses devis, ',
        'prix, taxes, produits, services, clients, ',
        'informations transmises et obligations ',
        'contractuelles.',
        '</p>',

        '<h3>3. Acceptation et signature</h3>',

        '<p>',
        'Le client peut accepter ou refuser un devis ',
        'et signer électroniquement. Les événements ',
        'et données nécessaires à la traçabilité ',
        'peuvent être conservés.',
        '</p>',

        '<h3>4. Paiements des devis</h3>',

        '<p>',
        'Pour le MVP, le client paie directement ',
        'le professionnel sur les moyens de paiement ',
        'indiqués par celui-ci. Devis Closer ne détient ',
        'pas, ne conserve pas et ne redistribue pas ',
        'les fonds du client.',
        '</p>',

        '<h3>5. Commission de service de 2 %</h3>',

        '<p>',
        'Lorsqu’un paiement de devis est enregistré ',
        'via le service, Devis Closer comptabilise ',
        'une commission de service de ',
        '<strong>2 %</strong> du montant brut.',
        '</p>',

        '<p>',
        'Dans le modèle de paiement direct, cette ',
        'commission n’est pas automatiquement ',
        'prélevée sur le transfert envoyé au ',
        'professionnel.',
        '</p>',

        '<h3>6. Abonnements</h3>',

        '<p>',
        'Les plans Free, Starter et Pro donnent ',
        'accès à des fonctionnalités différentes. ',
        'Les abonnements payants sont activés ',
        'après vérification du paiement.',
        '</p>',

        '<h3>7. Paiements d’abonnement</h3>',

        '<p>',
        'Les paiements MoMo et crypto peuvent ',
        'nécessiter un identifiant de transaction ',
        'et une preuve. L’activation est manuelle ',
        'dans le MVP et dépend de la vérification ',
        'administrative.',
        '</p>',

        '<h3>8. Fraude et litiges</h3>',

        '<p>',
        'Toute preuve falsifiée, tentative de fraude, ',
        'usurpation ou utilisation abusive peut ',
        'entraîner le rejet d’un paiement, la ',
        'suspension ou la suppression du compte.',
        '</p>',

        '<h3>9. Données</h3>',

        '<p>',
        'Les données sont utilisées pour fournir ',
        'le service, sécuriser les comptes, assurer ',
        'la traçabilité des devis et gérer les paiements.',
        '</p>',

        '<h3>10. Disponibilité</h3>',

        '<p>',
        'Le service est fourni avec des efforts ',
        'raisonnables de disponibilité. Devis Closer ',
        'ne garantit pas une disponibilité ininterrompue.',
        '</p>',

        '<h3>11. Propriété intellectuelle</h3>',

        '<p>',
        'Le logiciel, la marque et les éléments ',
        'graphiques de Devis Closer restent protégés ',
        'par les droits applicables.',
        '</p>',

        '<h3>12. Modification</h3>',

        '<p>',
        'Les présentes CGU peuvent évoluer.',
        '</p>',

        '<h3>13. Droit applicable</h3>',

        '<p>',
        'Les règles applicables et le règlement ',
        'des litiges seront déterminés selon les ',
        'informations légales communiquées par ',
        'l’exploitant du service et le pays concerné.',
        '</p>',

        '</div>'
    ])

    return layout(
        "CGU",
        body
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():

    user, redir = login_required()

    if redir:
        return redir

    code, plan = get_plan(
        user["id"]
    )

    stats = {}

    statuses = [
        ("devis", None),
        ("envoyes", "sent"),
        ("vus", "viewed"),
        ("negociation", "negotiation"),
        ("acceptes", "accepted"),
        ("signes", "signed"),
        ("payes", "paid"),
        ("refuses", "refused")
    ]

    for key, status in statuses:

        if status:

            row = db_execute(
                """
                SELECT COUNT(*) AS n
                FROM quotes
                WHERE user_id=%s
                AND status=%s
                """,
                (
                    user["id"],
                    status
                ),
                fetchone=True
            )

        else:

            row = db_execute(
                """
                SELECT COUNT(*) AS n
                FROM quotes
                WHERE user_id=%s
                """,
                (user["id"],),
                fetchone=True
            )

        stats[key] = int(
            row["n"]
        )

    revenue = db_execute(
        """
        SELECT COALESCE(
            SUM(gross_amount),0
        ) AS n

        FROM quote_payments

        WHERE professional_user_id=%s

        AND status='verified'
        """,
        (user["id"],),
        fetchone=True
    )["n"]

    potential = db_execute(
        """
        SELECT COALESCE(
            SUM(
                (
                    SELECT
                    COALESCE(
                        SUM(
                            i.quantity *
                            i.unit_price
                        ),0
                    )
                    FROM quote_items i
                    WHERE i.quote_id=q.id
                )
                - q.discount

                +

                (
                    GREATEST(
                        0,
                        (
                            SELECT
                            COALESCE(
                                SUM(
                                    i.quantity *
                                    i.unit_price
                                ),0
                            )
                            FROM quote_items i
                            WHERE i.quote_id=q.id
                        )
                        - q.discount
                    )
                    * q.tax_rate / 100
                )
            ),
            0
        ) AS n

        FROM quotes q

        WHERE q.user_id=%s

        AND q.status NOT IN
        (
            'refused',
            'expired',
            'paid'
        )
        """,
        (user["id"],),
        fetchone=True
    )["n"]

    conversion = (
        round(
            stats["acceptes"]
            /
            stats["envoyes"]
            * 100,
            1
        )
        if stats["envoyes"]
        else 0
    )

    rows = db_execute(
        """
        SELECT
            q.*,
            c.name AS customer_name

        FROM quotes q

        LEFT JOIN customers c
            ON c.id=q.customer_id

        WHERE q.user_id=%s

        ORDER BY q.created_at DESC

        LIMIT 10
        """,
        (user["id"],),
        fetchall=True
    )

    table = ''.join(

        '<tr>'
        '<td>'
        + esc(r["quote_number"])
        + '</td>'

        '<td>'
        + esc(
            r["customer_name"]
            or "-"
        )
        + '</td>'

        '<td class="status '
        + esc(r["status"])
        + '">'
        + esc(r["status"])
        + '</td>'

        '<td>'
        '<a href="/devis/'
        + str(r["id"])
        + '">Ouvrir</a>'
        '</td>'

        '</tr>'

        for r in rows
    )

    body = ''.join([

        '<h1>',
        'Bonjour ',
        esc(user["full_name"]),
        ' 👋',
        '</h1>',

        '<p class="muted">',
        'Plan <strong>',
        esc(plan["name"]),
        '</strong>.',
        '</p>',

        '<div class="stats">',

        '<div class="stat">',
        '<span class="muted">',
        'Revenus encaissés',
        '</span>',
        '<b>',
        money(revenue),
        ' ',
        esc(user["currency"]),
        '</b>',
        '</div>',

        '<div class="stat">',
        '<span class="muted">',
        'Potentiel',
        '</span>',
        '<b>',
        money(potential),
        ' ',
        esc(user["currency"]),
        '</b>',
        '</div>',

        '<div class="stat">',
        '<span class="muted">',
        'Devis',
        '</span>',
        '<b>',
        str(stats["devis"]),
        '</b>',
        '</div>',

        '<div class="stat">',
        '<span class="muted">',
        'Conversion',
        '</span>',
        '<b>',
        str(conversion),
        '%',
        '</b>',
        '</div>',

        '</div>',

        '<br>',

        '<div class="actions">',

        '<a class="btn" href="/nouveau-devis">',
        '+ Nouveau devis',
        '</a>',

        '<a class="btn secondary" href="/abonnement">',
        'Mon abonnement',
        '</a>',

        '<a class="btn secondary" href="/notifications">',
        'Notifications',
        '</a>',

        '</div>',

        '<div class="card">',

        '<h2>Derniers devis</h2>',

        '<div class="tablewrap">',

        '<table class="table">',

        '<tr>',
        '<th>N°</th>',
        '<th>Client</th>',
        '<th>Statut</th>',
        '<th></th>',
        '</tr>',

        table
        or
        '<tr>'
        '<td colspan="4">'
        'Aucun devis.'
        '</td>'
        '</tr>',

        '</table>',

        '</div>',

        '</div>'
    ])

    return layout(
        "Dashboard",
        body
    )


# ============================================================
# CLIENTS
# ============================================================

@app.route("/clients")
def clients():

    user, redir = login_required()

    if redir:
        return redir

    rows = db_execute(
        """
        SELECT *
        FROM customers
        WHERE user_id=%s
        ORDER BY created_at DESC
        """,
        (user["id"],),
        fetchall=True
    )

    items = ''.join(

        '<tr>'

        '<td>'
        + esc(r["name"])
        + '</td>'

        '<td>'
        + esc(
            r["company"]
            or "-"
        )
        + '</td>'

        '<td>'
        + esc(
            r["email"]
            or "-"
        )
        + '</td>'

        '<td>'
        + esc(
            r["phone"]
            or "-"
        )
        + '</td>'

        '</tr>'

        for r in rows
    )

    body = ''.join([

        '<div class="actions">',

        '<a class="btn" href="/clients/nouveau">',
        '+ Ajouter un client',
        '</a>',

        '</div>',

        '<div class="card">',

        '<h1>Clients</h1>',

        '<div class="tablewrap">',

        '<table class="table">',

        '<tr>',
        '<th>Nom</th>',
        '<th>Entreprise</th>',
        '<th>Email</th>',
        '<th>Téléphone</th>',
        '</tr>',

        items
        or
        '<tr>'
        '<td colspan="4">'
        'Aucun client.'
        '</td>'
        '</tr>',

        '</table>',

        '</div>',

        '</div>'
    ])

    return layout(
        "Clients",
        body
    )


@app.route(
    "/clients/nouveau",
    methods=["GET", "POST"]
)
def client_nouveau():

    user, redir = login_required()

    if redir:
        return redir

    code, plan = get_plan(
        user["id"]
    )

    if request.method == "POST":

        check_csrf()

        if (
            plan["clients"] is not None
            and client_count(user["id"])
            >= plan["clients"]
        ):

            return layout(
                "Client",
                '<div class="notice danger">'
                'Votre plan '
                + esc(plan["name"])
                + ' a atteint sa limite de clients.'
                '</div>'
            )

        name = request.form.get(
            "name",
            ""
        ).strip()

        if not name:

            return layout(
                "Client",
                '<div class="notice danger">'
                'Le nom est obligatoire.'
                '</div>'
                +
                customer_form()
            )

        db_execute(
            """
            INSERT INTO customers
            (
                user_id,
                name,
                company,
                email,
                phone,
                address,
                country,
                notes
            )
            VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                user["id"],
                name,
                request.form.get("company"),
                request.form.get("email"),
                request.form.get("phone"),
                request.form.get("address"),
                request.form.get("country"),
                request.form.get("notes")
            ),
            commit=True
        )

        return redirect(
            "/clients"
        )

    return layout(
        "Nouveau client",
        customer_form()
    )


def customer_form():

    return ''.join([

        '<form class="form card" method="post">',

        csrf_field(),

        '<h1>Nouveau client</h1>',

        '<div class="field">',
        '<label>Nom *</label>',
        '<input name="name" required>',
        '</div>',

        '<div class="row">',

        '<div class="field">',
        '<label>Entreprise</label>',
        '<input name="company">',
        '</div>',

        '<div class="field">',
        '<label>Email</label>',
        '<input type="email" name="email">',
        '</div>',

        '</div>',

        '<div class="row">',

        '<div class="field">',
        '<label>Téléphone</label>',
        '<input name="phone">',
        '</div>',

        '<div class="field">',
        '<label>Pays</label>',
        '<input name="country">',
        '</div>',

        '</div>',

        '<div class="field">',
        '<label>Adresse</label>',
        '<input name="address">',
        '</div>',

        '<div class="field">',
        '<label>Notes</label>',
        '<textarea name="notes"></textarea>',
        '</div>',

        '<button class="btn" type="submit">',
        'Enregistrer',
        '</button>',

        '</form>'
    ])


# ============================================================
# NOUVEAU DEVIS
# ============================================================

@app.route(
    "/nouveau-devis",
    methods=["GET", "POST"]
)
def nouveau_devis():

    user, redir = login_required()

    if redir:
        return redir

    allowed, code, limit = can_create_quote(
        user["id"]
    )

    if request.method == "POST":

        check_csrf()

        if not allowed:

            return layout(
                "Nouveau devis",
                '<div class="notice danger">'
                'Limite mensuelle atteinte pour le plan '
                + esc(
                    PLANS[code]["name"]
                )
                + '.'
                '</div>'
            )

        customer_id = (
            request.form.get(
                "customer_id"
            )
            or None
        )

        number = (
            "DC-"
            + datetime.now().strftime(
                "%Y%m%d"
            )
            + "-"
            + secrets.token_hex(3).upper()
        )

        token = secrets.token_urlsafe(
            32
        )

        currency = (
            request.form.get(
                "currency",
                user["currency"]
            )
            .upper()
            [:10]
        )

        try:

            discount = Decimal(
                request.form.get(
                    "discount",
                    "0"
                )
                or "0"
            )

            tax_rate = Decimal(
                request.form.get(
                    "tax_rate",
                    "0"
                )
                or "0"
            )

        except InvalidOperation:

            return layout(
                "Nouveau devis",
                '<div class="notice danger">'
                'Remise ou taxe invalide.'
                '</div>'
                +
                quote_form(
                    user["id"]
                )
            )

        descriptions = request.form.getlist(
            "description[]"
        )

        quantities = request.form.getlist(
            "quantity[]"
        )

        prices = request.form.getlist(
            "unit_price[]"
        )

        items = []

        for description, quantity, price in zip(
            descriptions,
            quantities,
            prices
        ):

            description = (
                description
                .strip()
            )

            if not description:
                continue

            try:

                qty = Decimal(
                    quantity or "1"
                )

                unit_price = Decimal(
                    price or "0"
                )

            except InvalidOperation:

                continue

            if (
                qty <= 0
                or unit_price < 0
            ):
                continue

            items.append(
                (
                    description,
                    qty,
                    unit_price
                )
            )

        if not items:

            return layout(
                "Nouveau devis",
                '<div class="notice danger">'
                'Ajoutez au moins une ligne de prestation.'
                '</div>'
                +
                quote_form(
                    user["id"]
                )
            )

        conn = db_connect()

        try:

            with conn.cursor(
                cursor_factory=RealDictCursor
            ) as cur:

                cur.execute(
                    """
                    INSERT INTO quotes
                    (
                        user_id,
                        customer_id,
                        quote_number,
                        public_token,
                        status,
                        currency,
                        discount,
                        tax_rate,
                        terms,
                        expires_at
                    )
                    VALUES
                    (
                        %s,%s,%s,%s,'draft',
                        %s,%s,%s,%s,%s
                    )
                    RETURNING id
                    """,
                    (
                        user["id"],
                        customer_id,
                        number,
                        token,
                        currency,
                        discount,
                        tax_rate,
                        request.form.get(
                            "terms"
                        ),
                        request.form.get(
                            "expires_at"
                        )
                        or None
                    )
                )

                quote_id = cur.fetchone()["id"]

                for (
                    description,
                    quantity,
                    unit_price
                ) in items:

                    cur.execute(
                        """
                        INSERT INTO quote_items
                        (
                            quote_id,
                            description,
                            quantity,
                            unit_price
                        )
                        VALUES
                        (%s,%s,%s,%s)
                        """,
                        (
                            quote_id,
                            description,
                            quantity,
                            unit_price
                        )
                    )

                cur.execute(
                    """
                    INSERT INTO quote_events
                    (
                        quote_id,
                        event_type,
                        note
                    )
                    VALUES
                    (
                        %s,
                        'created',
                        'Devis créé'
                    )
                    """,
                    (quote_id,)
                )

            conn.commit()

        finally:
            conn.close()

        return redirect(
            "/devis/"
            + str(quote_id)
        )

    return layout(
        "Nouveau devis",
        quote_form(
            user["id"],
            user["currency"]
        )
    )


def quote_form(
    user_id,
    currency="XOF"
):

    customers = db_execute(
        """
        SELECT id,name
        FROM customers
        WHERE user_id=%s
        ORDER BY name
        """,
        (user_id,),
        fetchall=True
    )

    options = (
        '<option value="">'
        'Client sans fiche'
        '</option>'
        +
        ''.join(
            '<option value="'
            + str(c["id"])
            + '">'
            + esc(c["name"])
            + '</option>'
            for c in customers
        )
    )

    rows = ''.join(

        '<div class="row">'

        '<div class="field">',
        '<label>Description</label>',
        '<input name="description[]" required>',
        '</div>',

        '<div class="field">',
        '<label>Qté</label>',
        '<input type="number" step="0.01" ',
        'name="quantity[]" value="1">',
        '</div>',

        '<div class="field">',
        '<label>Prix unitaire</label>',
        '<input type="number" step="0.01" ',
        'min="0" name="unit_price[]" value="0">',
        '</div>',

        '</div>'

        for _ in range(3)
    )

    return ''.join([

        '<form class="card" method="post">',

        csrf_field(),

        '<h1>Nouveau devis</h1>',

        '<div class="field">',

        '<label>Client</label>',

        '<select name="customer_id">',

        options,

        '</select>',

        '</div>',

        rows,

        '<div class="row">',

        '<div class="field">',
        '<label>Devise</label>',
        '<input name="currency" value="',
        esc(currency),
        '">',
        '</div>',

        '<div class="field">',
        '<label>Remise</label>',
        '<input type="number" ',
        'step="0.01" min="0" ',
        'name="discount" value="0">',
        '</div>',

        '</div>',

        '<div class="row">',

        '<div class="field">',
        '<label>Taxe (%)</label>',
        '<input type="number" ',
        'step="0.001" min="0" ',
        'name="tax_rate" value="0">',
        '</div>',

        '<div class="field">',
        '<label>Date d’expiration</label>',
        '<input type="date" ',
        'name="expires_at">',
        '</div>',

        '</div>',

        '<div class="field">',
        '<label>Conditions</label>',
        '<textarea name="terms">',
        'Paiement selon les modalités convenues ',
        'avec le professionnel.',
        '</textarea>',
        '</div>',

        '<button class="btn" type="submit">',
        'Créer le devis',
        '</button>',

        '</form>'
    ])


# ============================================================
# DETAIL DEVIS
# ============================================================

@app.route("/devis/<int:quote_id>")
def quote_detail(quote_id):

    user, redir = login_required()

    if redir:
        return redir

    quote = quote_access(
        quote_id,
        user["id"]
    )

    customer = None

    if quote["customer_id"]:

        customer = db_execute(
            """
            SELECT *
            FROM customers
            WHERE id=%s
            """,
            (
                quote["customer_id"],
            ),
            fetchone=True
        )

    items = db_execute(
        """
        SELECT *
        FROM quote_items
        WHERE quote_id=%s
        ORDER BY id
        """,
        (quote_id,),
        fetchall=True
    )

    subtotal, discount, tax, total = quote_totals(
        quote_id
    )

    public_link = (
        request.host_url.rstrip("/")
        + "/q/"
        + quote["public_token"]
    )

    itemrows = ''.join(

        '<tr>'

        '<td>'
        + esc(i["description"])
        + '</td>'

        '<td>'
        + money(i["quantity"])
        + '</td>'

        '<td>'
        + money(i["unit_price"])
        + '</td>'

        '<td>'
        + money(
            Decimal(
                str(i["quantity"])
            )
            *
            Decimal(
                str(i["unit_price"])
            )
        )
        + '</td>'

        '</tr>'

        for i in items
    )

    body = ''.join([

        '<div class="actions">',

        '<a class="btn" href="/devis/',
        str(quote_id),
        '/envoyer">',
        'Envoyer',
        '</a>',

        '<a class="btn secondary" href="',
        esc(public_link),
        '" target="_blank">',
        'Voir le lien public',
        '</a>',

        '<a class="btn secondary" href="/devis/',
        str(quote_id),
        '/imprimer" target="_blank">',
        'Imprimer / PDF',
        '</a>',

        '<a class="btn gold" href="/closer/',
        str(quote_id),
        '">',
        'Closer',
        '</a>',

        '</div>',

        '<div class="quote-paper">',

        '<h1>DEVIS ',
        esc(quote["quote_number"]),
        '</h1>',

        '<p>',
        'Statut : <strong>',
        esc(quote["status"]),
        '</strong>',
        '</p>',

        '<p>',
        'Client : <strong>',
        esc(
            customer["name"]
            if customer
            else "-"
        ),
        '</strong>',
        '</p>',

        '<table>',

        '<tr>',
        '<th>Prestation</th>',
        '<th>Qté</th>',
        '<th>PU</th>',
        '<th>Total</th>',
        '</tr>',

        itemrows,

        '</table>',

        '<p class="total">',

        'Sous-total : ',
        money(subtotal),
        ' ',
        esc(quote["currency"]),

        '<br>Remise : ',
        money(discount),

        '<br>Taxe : ',
        money(tax),

        '<br><strong>Total : ',
        money(total),
        ' ',
        esc(quote["currency"]),
        '</strong>',

        '</p>',

        '<p>',
        esc(
            quote["terms"]
            or ""
        ),
        '</p>',

        '</div>'
    ])

    return layout(
        "Devis " + quote["quote_number"],
        body
    )


# ============================================================
# ENVOI DEVIS
# ============================================================

@app.route(
    "/devis/<int:quote_id>/envoyer"
)
def quote_send(quote_id):

    user, redir = login_required()

    if redir:
        return redir

    quote = quote_access(
        quote_id,
        user["id"]
    )

    customer = None

    if quote["customer_id"]:

        customer = db_execute(
            """
            SELECT *
            FROM customers
            WHERE id=%s
            """,
            (
                quote["customer_id"],
            ),
            fetchone=True
        )

    link = (
        request.host_url.rstrip("/")
        + "/q/"
        + quote["public_token"]
    )

    customer_name = (
        customer["name"]
        if customer
        else ""
    )

    message = (
        "Bonjour "
        + customer_name
        + ", voici votre devis "
        + quote["quote_number"]
        + ". Vous pouvez le consulter ici : "
        + link
    )

    phone = ""

    if customer:
        phone = (
            customer["phone"]
            or ""
        )

    wa = (
        "https://wa.me/"
        + re.sub(
            r"\D",
            "",
            phone
        )
        + "?text="
        + urlquote(message)
    )

    db_execute(
        """
        UPDATE quotes
        SET status='sent'
        WHERE id=%s
        AND status='draft'
        """,
        (quote_id,),
        commit=True
    )

    add_event(
        quote_id,
        "sent",
        "Devis préparé pour envoi"
    )

    body = ''.join([

        '<div class="card">',

        '<h1>Envoyer le devis</h1>',

        '<p>',
        'Le lien sécurisé est prêt.',
        '</p>',

        '<div class="notice">',
        esc(link),
        '</div>',

        '<div class="actions">',

        '<a class="btn" href="',
        esc(wa),
        '" target="_blank">',
        'Envoyer sur WhatsApp',
        '</a>',

        '<a class="btn secondary" href="mailto:?subject=',
        urlquote(
            "Devis "
            + quote["quote_number"]
        ),
        '&body=',
        urlquote(message),
        '">',
        'Envoyer par email',
        '</a>',

        '</div>',

        '</div>'
    ])

    return layout(
        "Envoyer",
        body
    )


# ============================================================
# IMPRESSION DEVIS
# ============================================================

@app.route(
    "/devis/<int:quote_id>/imprimer"
)
def quote_print(quote_id):

    user, redir = login_required()

    if redir:
        return redir

    quote = quote_access(
        quote_id,
        user["id"]
    )

    return public_quote_page(
        quote,
        owner_view=True,
        printable=True
    )


# ============================================================
# PAGE PUBLIQUE DEVIS
# ============================================================

def public_quote_page(
    quote,
    owner_view=False,
    printable=False
):

    customer = None

    if quote["customer_id"]:

        customer = db_execute(
            """
            SELECT *
            FROM customers
            WHERE id=%s
            """,
            (
                quote["customer_id"],
            ),
            fetchone=True
        )

    items = db_execute(
        """
        SELECT *
        FROM quote_items
        WHERE quote_id=%s
        ORDER BY id
        """,
        (
            quote["id"],
        ),
        fetchall=True
    )

    subtotal, discount, tax, total = quote_totals(
        quote["id"]
    )

    professional = db_execute(
        """
        SELECT *
        FROM users
        WHERE id=%s
        """,
        (
            quote["user_id"],
        ),
        fetchone=True
    )

    rows = ''.join(

        '<tr>'

        '<td>'
        + esc(i["description"])
        + '</td>'

        '<td>'
        + money(i["quantity"])
        + '</td>'

        '<td>'
        + money(i["unit_price"])
        + '</td>'

        '<td>'
        + money(
            Decimal(
                str(i["quantity"])
            )
            *
            Decimal(
                str(i["unit_price"])
            )
        )
        + '</td>'

        '</tr>'

        for i in items
    )

    if owner_view:

        actions = ""

    else:

        actions = ''.join([

            '<div class="actions">',

            '<a class="btn green" href="/q/',
            esc(quote["public_token"]),
            '/accepter">',
            'Accepter',
            '</a>',

            '<a class="btn gold" href="/q/',
            esc(quote["public_token"]),
            '/payer">',
            'Accepter et payer',
            '</a>',

            '<a class="btn green" href="/q/',
            esc(quote["public_token"]),
            '/signer">',
            'Signer',
            '</a>',

            '<a class="btn secondary" href="/q/',
            esc(quote["public_token"]),
            '/modifier">',
            'Demander une modification',
            '</a>',

            '<a class="btn red" href="/q/',
            esc(quote["public_token"]),
            '/refuser">',
            'Refuser',
            '</a>',

            '</div>'
        ])

    body = ''.join([

        '<div class="quote-paper">',

        '<div style="text-align:center">',

        '<h1>DEVIS</h1>',

        '<p>',
        '<strong>',
        esc(quote["quote_number"]),
        '</strong>',
        '</p>',

        '</div>',

        '<p>',

        '<strong>Professionnel :</strong> ',

        esc(
            professional["company_name"]
            or professional["full_name"]
        ),

        '<br>',

        esc(
            professional["email"]
        ),

        '<br>',

        esc(
            professional["phone"]
            or ""
        ),

        '</p>',

        '<p>',

        '<strong>Client :</strong> ',

        esc(
            customer["name"]
            if customer
            else "-"
        ),

        '</p>',

        '<table>',

        '<tr>',
        '<th>Prestation</th>',
        '<th>Qté</th>',
        '<th>Prix</th>',
        '<th>Total</th>',
        '</tr>',

        rows,

        '</table>',

        '<p class="total">',

        'Sous-total : ',
        money(subtotal),
        ' ',
        esc(quote["currency"]),

        '<br>Remise : ',
        money(discount),

        '<br>Taxe : ',
        money(tax),

        '<br><strong>Total : ',
        money(total),
        ' ',
        esc(quote["currency"]),
        '</strong>',

        '</p>',

        '<p>',
        esc(
            quote["terms"]
            or ""
        ),
        '</p>',

        '</div>',

        actions
    ])

    if printable:

        printable_html = ''.join([

            '<!doctype html>',

            '<html>',

            '<head>',

            '<meta charset="utf-8">',

            '<title>',
            'Devis ',
            esc(quote["quote_number"]),
            '</title>',

            '<style>',

            'body{',
            'font-family:Arial;',
            'background:#eee;',
            'padding:30px;',
            '}',

            '.quote-paper{',
            'background:#fff;',
            'padding:30px;',
            'max-width:850px;',
            'margin:auto;',
            '}',

            '.quote-paper table{',
            'width:100%;',
            'border-collapse:collapse;',
            '}',

            '.quote-paper th,',
            '.quote-paper td{',
            'border-bottom:1px solid #ddd;',
            'padding:10px;',
            'text-align:left;',
            '}',

            '.total{',
            'text-align:right;',
            'font-size:18px;',
            '}',

            '.actions{',
            'display:none;',
            '}',

            '@media print{',
            'body{',
            'background:#fff;',
            'padding:0;',
            '}',
            '}',

            '</style>',

            '</head>',

            '<body>',

            body,

            '<script>',
            'window.print();',
            '</script>',

            '</body>',

            '</html>'
        ])

        return render_template_string(
            printable_html
        )

    return layout(
        "Devis " + quote["quote_number"],
        body
    )


# ============================================================
# DEVIS PUBLIC
# ============================================================

@app.route("/q/<token>")
def public_quote(token):

    quote = db_execute(
        """
        SELECT *
        FROM quotes
        WHERE public_token=%s
        """,
        (token,),
        fetchone=True
    )

    if not quote:
        abort(404)

    if quote["status"] == "draft":

        db_execute(
            """
            UPDATE quotes

            SET
                status='sent',
                viewed_at=NOW()

            WHERE id=%s
            """,
            (
                quote["id"],
            ),
            commit=True
        )

    else:

        db_execute(
            """
            UPDATE quotes

            SET viewed_at=
                COALESCE(
                    viewed_at,
                    NOW()
                )

            WHERE id=%s
            """,
            (
                quote["id"],
            ),
            commit=True
        )

    add_event(
        quote["id"],
        "viewed",
        "Devis consulté"
    )

    return public_quote_page(
        quote
    )


# ============================================================
# ACCEPTER DEVIS
# ============================================================

@app.route(
    "/q/<token>/accepter"
)
def public_accept(token):

    quote = db_execute(
        """
        SELECT *
        FROM quotes
        WHERE public_token=%s
        """,
        (token,),
        fetchone=True
    )

    if not quote:
        abort(404)

    db_execute(
        """
        UPDATE quotes

        SET
            status='accepted',
            accepted_at=NOW()

        WHERE id=%s

        AND status NOT IN
        (
            'paid',
            'refused'
        )
        """,
        (
            quote["id"],
        ),
        commit=True
    )

    add_event(
        quote["id"],
        "accepted",
        "Client a accepté le devis"
    )

    notify(
        quote["user_id"],
        "Devis accepté",
        "Le devis "
        + quote["quote_number"]
        + " a été accepté."
    )

    return layout(
        "Devis accepté",
        ''.join([

            '<div class="card">',

            '<h1>Devis accepté ✅</h1>',

            '<p>',
            'Merci. Le professionnel a été informé.',
            '</p>',

            '<a class="btn gold" href="/q/',
            esc(quote["public_token"]),
            '/payer">',
            'Accepter et payer',
            '</a>',

            '</div>'
        ])
    )


# ============================================================
# REFUSER DEVIS
# ============================================================

@app.route(
    "/q/<token>/refuser"
)
def public_refuse(token):

    quote = db_execute(
        """
        SELECT *
        FROM quotes
        WHERE public_token=%s
        """,
        (token,),
        fetchone=True
    )

    if not quote:
        abort(404)

    db_execute(
        """
        UPDATE quotes

        SET
            status='refused',
            refused_at=NOW()

        WHERE id=%s
        """,
        (
            quote["id"],
        ),
        commit=True
    )

    add_event(
        quote["id"],
        "refused",
        "Client a refusé le devis"
    )

    notify(
        quote["user_id"],
        "Devis refusé",
        "Le devis "
        + quote["quote_number"]
        + " a été refusé."
    )

    return layout(
        "Devis refusé",
        '<div class="card">'
        '<h1>Devis refusé</h1>'
        '<p>Votre réponse a été enregistrée.</p>'
        '</div>'
    )


# ============================================================
# MODIFICATION / NÉGOCIATION
# ============================================================

@app.route(
    "/q/<token>/modifier",
    methods=["GET", "POST"]
)
def public_modify(token):

    quote = db_execute(
        """
        SELECT *
        FROM quotes
        WHERE public_token=%s
        """,
        (token,),
        fetchone=True
    )

    if not quote:
        abort(404)

    if request.method == "POST":

        check_csrf()

        note = request.form.get(
            "note",
            ""
        ).strip()

        if not note:

            return layout(
                "Modification",
                '<div class="notice danger">'
                'Écrivez votre demande.'
                '</div>'
            )

        db_execute(
            """
            UPDATE quotes
            SET status='negotiation'
            WHERE id=%s
            """,
            (
                quote["id"],
            ),
            commit=True
        )

        add_event(
            quote["id"],
            "negotiation",
            note
        )

        notify(
            quote["user_id"],
            "Demande de modification",
            "Le client a demandé une modification "
            "pour le devis "
            + quote["quote_number"]
            + "."
        )

        return layout(
            "Demande envoyée",
            '<div class="card">'
            '<h1>Demande envoyée</h1>'
            '<p>',
            'Le professionnel a été informé.',
            '</p>'
            '</div>'
        )

    return layout(
        "Demander une modification",
        ''.join([

            '<form class="form card" method="post">',

            csrf_field(),

            '<h1>Demander une modification</h1>',

            '<div class="field">',

            '<label>Votre demande</label>',

            '<textarea name="note" required>',
            '</textarea>',

            '</div>',

            '<button class="btn" type="submit">',
            'Envoyer',
            '</button>',

            '</form>'
        ])
    )


# ============================================================
# SIGNATURE ÉLECTRONIQUE
# ============================================================

@app.route(
    "/q/<token>/signer",
    methods=["GET", "POST"]
)
def public_sign(token):

    quote = db_execute(
        """
        SELECT *
        FROM quotes
        WHERE public_token=%s
        """,
        (token,),
        fetchone=True
    )

    if not quote:
        abort(404)

    if request.method == "POST":

        check_csrf()

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        if not name:

            return layout(
                "Signature",
                '<div class="notice danger">'
                'Le nom est obligatoire.'
                '</div>'
            )

        db_execute(
            """
            INSERT INTO signatures
            (
                quote_id,
                signer_name,
                signer_email,
                ip_address
            )
            VALUES
            (%s,%s,%s,%s)

            ON CONFLICT(quote_id)

            DO UPDATE SET
                signer_name=EXCLUDED.signer_name,
                signer_email=EXCLUDED.signer_email,
                ip_address=EXCLUDED.ip_address,
                signed_at=NOW()
            """,
            (
                quote["id"],
                name,
                email,
                request.remote_addr
            ),
            commit=True
        )

        db_execute(
            """
            UPDATE quotes

            SET
                status='signed',
                signed_at=NOW()

            WHERE id=%s
            """,
            (
                quote["id"],
            ),
            commit=True
        )

        add_event(
            quote["id"],
            "signed",
            "Signature électronique enregistrée"
        )

        notify(
            quote["user_id"],
            "Devis signé",
            "Le devis "
            + quote["quote_number"]
            + " vient d’être signé."
        )

        return layout(
            "Signature enregistrée",
            ''.join([

                '<div class="card">',

                '<h1>Signature enregistrée ✅</h1>',

                '<p>',
                'Merci, votre signature a été enregistrée.',
                '</p>',

                '<a class="btn gold" href="/q/',
                esc(quote["public_token"]),
                '/payer">',
                'Accepter et payer',
                '</a>',

                '</div>'
            ])
        )

    return layout(
        "Signer",
        ''.join([

            '<form class="form card" method="post">',

            csrf_field(),

            '<h1>Signer le devis</h1>',

            '<div class="field">',

            '<label>Nom complet *</label>',

            '<input name="name" required>',

            '</div>',

            '<div class="field">',

            '<label>Email</label>',

            '<input type="email" name="email">',

            '</div>',

            '<label class="check">',

            '<input type="checkbox" required>',

            '<span>',
            'Je confirme que cette signature ',
            'correspond à mon intention d’accepter ',
            'le devis.',
            '</span>',

            '</label>',

            '<br>',

            '<button class="btn green" type="submit">',
            'Signer électroniquement',
            '</button>',

            '</form>'
        ])
    )


# ============================================================
# PAIEMENT DEVIS CLIENT
# ============================================================

@app.route(
    "/q/<token>/payer",
    methods=["GET", "POST"]
)
def public_pay(token):

    quote = db_execute(
        """
        SELECT *
        FROM quotes
        WHERE public_token=%s
        """,
        (token,),
        fetchone=True
    )

    if not quote:
        abort(404)

    professional = db_execute(
        """
        SELECT *
        FROM users
        WHERE id=%s
        """,
        (
            quote["user_id"],
        ),
        fetchone=True
    )

    _, _, _, total = quote_totals(
        quote["id"]
    )

    if request.method == "POST":

        check_csrf()

        method = request.form.get(
            "method",
            ""
        ).strip()

        transaction_id = request.form.get(
            "transaction_id",
            ""
        ).strip()

        payer = request.form.get(
            "payer_name",
            ""
        ).strip()

        proof = request.files.get(
            "proof"
        )

        if (
            not method
            or len(transaction_id) < 3
        ):

            return layout(
                "Paiement",
                '<div class="notice danger">'
                'Méthode et identifiant de transaction '
                'obligatoires.'
                '</div>'
            )

        if (
            not proof
            or not allowed_image(proof)
        ):

            return layout(
                "Paiement",
                '<div class="notice danger">'
                'Une capture/preuve JPG, PNG ou WEBP '
                'est obligatoire.'
                '</div>'
            )

        data = proof.read()

        if len(data) > 2 * 1024 * 1024:

            return layout(
                "Paiement",
                '<div class="notice danger">'
                'La preuve ne doit pas dépasser 2 Mo.'
                '</div>'
            )

        commission = (
            total
            *
            COMMISSION_RATE
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        net = (
            total
            - commission
        )

        try:

            db_execute(
                """
                INSERT INTO quote_payments
                (
                    quote_id,
                    professional_user_id,
                    gross_amount,
                    commission_amount,
                    net_amount,
                    currency,
                    method,
                    transaction_id,
                    proof_data,
                    proof_mime,
                    proof_filename,
                    payer_name
                )
                VALUES
                (
                    %s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s
                )
                """,
                (
                    quote["id"],
                    quote["user_id"],
                    total,
                    commission,
                    net,
                    quote["currency"],
                    method,
                    transaction_id,
                    data,
                    proof.mimetype,
                    secure_filename(
                        proof.filename
                    ),
                    payer
                ),
                commit=True
            )

        except psycopg2.errors.UniqueViolation:

            return layout(
                "Paiement",
                '<div class="notice danger">'
                'Cet identifiant de transaction '
                'a déjà été utilisé.'
                '</div>'
            )

        db_execute(
            """
            UPDATE quotes

            SET status='accepted'

            WHERE id=%s

            AND status NOT IN
            (
                'paid',
                'refused'
            )
            """,
            (
                quote["id"],
            ),
            commit=True
        )

        add_event(
            quote["id"],
            "payment_pending",
            "Paiement déclaré par le client"
        )

        notify(
            quote["user_id"],
            "Paiement en attente",
            "Un paiement a été déclaré pour le devis "
            + quote["quote_number"]
            + "."
        )

        return layout(
            "Paiement envoyé",
            ''.join([

                '<div class="card">',

                '<h1>Paiement déclaré</h1>',

                '<p>',
                'Le paiement est en attente de ',
                'vérification par le professionnel.',
                '</p>',

                '<p>',
                'Montant : <strong>',
                money(total),
                ' ',
                esc(quote["currency"]),
                '</strong>',
                '</p>',

                '</div>'
            ])
        )

    momo_number = (
        professional["momo_number"]
        or "Non configuré"
    )

    momo_name = (
        professional["momo_name"]
        or "Non configuré"
    )

    bsc = (
        professional["usdt_bep20"]
        or professional["bnb_address"]
        or "Non configuré"
    )

    tron = (
        professional["usdt_trc20"]
        or professional["tron_address"]
        or "Non configuré"
    )

    body = ''.join([

        '<div class="card">',

        '<h1>Accepter et payer</h1>',

        '<p>',
        '<strong>Montant : ',
        money(total),
        ' ',
        esc(quote["currency"]),
        '</strong>',
        '</p>',

        '<div class="notice">',

        'Le paiement est effectué ',
        '<strong>directement au professionnel</strong>.',
        ' Devis Closer ne détient pas les fonds.',

        '</div>',

        '<h3>MoMo</h3>',

        '<p>',
        'Nom : <strong>',
        esc(momo_name),
        '</strong>',

        '<br>',

        'Numéro : <strong>',
        esc(momo_number),
        '</strong>',

        '</p>',

        '<h3>Crypto</h3>',

        '<p>',

        'USDT BEP20 / BNB : ',
        '<strong>',
        esc(bsc),
        '</strong>',

        '<br>',

        'USDT TRC20 / TRON : ',
        '<strong>',
        esc(tron),
        '</strong>',

        '</p>',

        '</div>',

        '<form class="form card" ',
        'method="post" ',
        'enctype="multipart/form-data">',

        csrf_field(),

        '<div class="field">',

        '<label>Méthode de paiement</label>',

        '<select name="method" required>',

        '<option value="MoMo">MoMo</option>',

        '<option value="USDT BEP20">',
        'USDT BEP20',
        '</option>',

        '<option value="USDT TRC20">',
        'USDT TRC20',
        '</option>',

        '<option value="BNB">BNB</option>',

        '<option value="TRON">TRON</option>',

        '</select>',

        '</div>',

        '<div class="field">',

        '<label>Nom du payeur</label>',

        '<input name="payer_name">',

        '</div>',

        '<div class="field">',

        '<label>ID transaction / TXID *</label>',

        '<input name="transaction_id" required>',

        '</div>',

        '<div class="field">',

        '<label>Capture / preuve de paiement *</label>',

        '<input type="file" ',
        'name="proof" ',
        'accept="image/jpeg,image/png,image/webp" ',
        'required>',

        '</div>',

        '<p class="small muted">',

        'Commission de service Devis Closer : 2 %. ',
        'Elle est enregistrée à titre de service/comptabilité ',
        'et n’est pas automatiquement déduite du transfert ',
        'direct au professionnel dans ce MVP.',

        '</p>',

        '<button class="btn gold" type="submit">',
        'Déclarer le paiement',
        '</button>',

        '</form>'
    ])

    return layout(
        "Paiement du devis",
        body
    )


# ============================================================
# ABONNEMENT
# ============================================================

@app.route("/abonnement")
def abonnement():

    user, redir = login_required()

    if redir:
        return redir

    code, plan = get_plan(
        user["id"]
    )

    cards = []

    for plan_code in [
        "starter",
        "pro"
    ]:

        current = PLANS[
            plan_code
        ]

        cards.append(''.join([

            '<div class="card">',

            '<h2>',
            esc(current["name"]),
            '</h2>',

            '<div class="price">',
            money(current["price"]),
            ' XOF/mois',
            '</div>',

            '<a class="btn" href="/abonnement/payer/',
            plan_code,
            '">',
            'Choisir',
            '</a>',

            '</div>'
        ]))

    body = ''.join([

        '<div class="card">',

        '<h1>Mon abonnement</h1>',

        '<p>',
        'Plan actuel : <strong>',
        esc(plan["name"]),
        '</strong>',
        '</p>',

        '</div>',

        '<h2>Changer de plan</h2>',

        '<div class="grid">',

        ''.join(cards),

        '</div>'
    ])

    return layout(
        "Abonnement",
        body
    )


# ============================================================
# PAIEMENT ABONNEMENT
# ============================================================

@app.route(
    "/abonnement/payer/<plan_code>",
    methods=["GET", "POST"]
)
def subscription_pay(plan_code):

    user, redir = login_required()

    if redir:
        return redir

    if (
        plan_code not in PLANS
        or plan_code == "free"
    ):
        abort(404)

    plan = PLANS[
        plan_code
    ]

    if request.method == "POST":

        check_csrf()

        method = request.form.get(
            "method",
            ""
        ).strip()

        transaction_id = request.form.get(
            "transaction_id",
            ""
        ).strip()

        proof = request.files.get(
            "proof"
        )

        if (
            method == "MoMo"
            and not proof
        ):

            return layout(
                "Paiement abonnement",
                '<div class="notice danger">'
                'La capture de paiement est obligatoire '
                'pour MoMo.'
                '</div>'
            )

        if not transaction_id:

            return layout(
                "Paiement abonnement",
                '<div class="notice danger">'
                'L’identifiant de transaction est obligatoire.'
                '</div>'
            )

        data = None
        mime = None
        filename = None

        if proof and proof.filename:

            if not allowed_image(proof):

                return layout(
                    "Paiement abonnement",
                    '<div class="notice danger">'
                    'Format de preuve non accepté.'
                    '</div>'
                )

            data = proof.read()

            mime = proof.mimetype

            filename = secure_filename(
                proof.filename
            )

            if len(data) > 2 * 1024 * 1024:

                return layout(
                    "Paiement abonnement",
                    '<div class="notice danger">'
                    'Preuve limitée à 2 Mo.'
                    '</div>'
                )

        try:

            db_execute(
                """
                INSERT INTO subscription_payments
                (
                    user_id,
                    plan_code,
                    amount,
                    currency,
                    method,
                    transaction_id,
                    proof_data,
                    proof_mime,
                    proof_filename
                )
                VALUES
                (
                    %s,%s,%s,'XOF',
                    %s,%s,%s,%s,%s
                )
                """,
                (
                    user["id"],
                    plan_code,
                    plan["price"],
                    method,
                    transaction_id,
                    data,
                    mime,
                    filename
                ),
                commit=True
            )

        except psycopg2.errors.UniqueViolation:

            return layout(
                "Paiement abonnement",
                '<div class="notice danger">'
                'Cet identifiant de transaction '
                'existe déjà.'
                '</div>'
            )

        notify(
            user["id"],
            "Paiement reçu",
            "Votre paiement pour le plan "
            + plan["name"]
            + " est en attente de validation."
        )

        return layout(
            "Paiement envoyé",
            '<div class="card">'
            '<h1>Paiement envoyé</h1>'
            '<p>'
            'Votre paiement est en attente de '
            'vérification administrative.'
            '</p>'
            '</div>'
        )

    body = ''.join([

        '<div class="card">',

        '<h1>Payer le plan ',
        esc(plan["name"]),
        '</h1>',

        '<div class="price">',
        money(plan["price"]),
        ' XOF',
        '</div>',

        '<h3>MoMo</h3>',

        '<p>',

        'Nom : <strong>',
        esc(MOMO_NAME),
        '</strong>',

        '<br>',

        'Numéro : <strong>',
        esc(MOMO),
        '</strong>',

        '<br>',

        'International : <strong>',
        esc(MOMO_INT),
        '</strong>',

        '</p>',

        '<h3>Crypto</h3>',

        '<p>',

        'USDT BEP20 / BNB : <strong>',
        esc(BSC_ADDR),
        '</strong>',

        '<br>',

        'USDT TRC20 / TRON : <strong>',
        esc(TRON_ADDR),
        '</strong>',

        '</p>',

        '</div>',

        '<form class="form card" ',
        'method="post" ',
        'enctype="multipart/form-data">',

        csrf_field(),

        '<div class="field">',

        '<label>Méthode</label>',

        '<select name="method" required>',

        '<option>MoMo</option>',

        '<option>USDT TRC20</option>',

        '<option>USDT BEP20</option>',

        '<option>BNB</option>',

        '<option>TRON</option>',

        '</select>',

        '</div>',

        '<div class="field">',

        '<label>ID transaction / TXID</label>',

        '<input name="transaction_id" required>',

        '</div>',

        '<div class="field">',

        '<label>Capture / preuve de paiement</label>',

        '<input type="file" ',
        'name="proof" ',
        'accept="image/jpeg,image/png,image/webp">',

        '<p class="small muted">',
        'Obligatoire pour MoMo. ',
        'Pour la crypto, le TXID peut suffire ',
        'pour la vérification manuelle.',
        '</p>',

        '</div>',

        '<button class="btn gold" type="submit">',
        'Soumettre le paiement',
        '</button>',

        '</form>'
    ])

    return layout(
        "Paiement abonnement",
        body
    )


# ============================================================
# PROFIL
# ============================================================

@app.route(
    "/profil",
    methods=["GET", "POST"]
)
def profil():

    user, redir = login_required()

    if redir:
        return redir

    if request.method == "POST":

        check_csrf()

        db_execute(
            """
            UPDATE users

            SET
                full_name=%s,
                company_name=%s,
                phone=%s,
                address=%s,
                country=%s,
                currency=%s,
                momo_number=%s,
                momo_name=%s,
                usdt_trc20=%s,
                usdt_bep20=%s,
                bnb_address=%s,
                tron_address=%s

            WHERE id=%s
            """,
            (
                request.form.get(
                    "full_name"
                ),

                request.form.get(
                    "company_name"
                ),

                request.form.get(
                    "phone"
                ),

                request.form.get(
                    "address"
                ),

                request.form.get(
                    "country"
                ),

                request.form.get(
                    "currency"
                ),

                request.form.get(
                    "momo_number"
                ),

                request.form.get(
                    "momo_name"
                ),

                request.form.get(
                    "usdt_trc20"
                ),

                request.form.get(
                    "usdt_bep20"
                ),

                request.form.get(
                    "bnb_address"
                ),

                request.form.get(
                    "tron_address"
                ),

                user["id"]
            ),
            commit=True
        )

        return redirect(
            "/profil"
        )

    def field(name):

        return esc(
            user[name]
            or ""
        )

    body = ''.join([

        '<form class="form card" method="post">',

        csrf_field(),

        '<h1>Profil & paiements</h1>',

        '<p class="muted">',
        'Ces coordonnées seront affichées au client ',
        'sur la page de paiement de vos devis.',
        '</p>',

        '<div class="field">',
        '<label>Nom complet</label>',
        '<input name="full_name" value="',
        field("full_name"),
        '">',
        '</div>',

        '<div class="field">',
        '<label>Entreprise</label>',
        '<input name="company_name" value="',
        field("company_name"),
        '">',
        '</div>',

        '<div class="row">',

        '<div class="field">',
        '<label>Téléphone</label>',
        '<input name="phone" value="',
        field("phone"),
        '">',
        '</div>',

        '<div class="field">',
        '<label>Devise</label>',
        '<input name="currency" value="',
        field("currency"),
        '">',
        '</div>',

        '</div>',

        '<div class="field">',
        '<label>Adresse</label>',
        '<input name="address" value="',
        field("address"),
        '">',
        '</div>',

        '<div class="row">',

        '<div class="field">',
        '<label>MoMo numéro</label>',
        '<input name="momo_number" value="',
        field("momo_number"),
        '">',
        '</div>',

        '<div class="field">',
        '<label>MoMo nom</label>',
        '<input name="momo_name" value="',
        field("momo_name"),
        '">',
        '</div>',

        '</div>',

        '<div class="field">',
        '<label>USDT TRC20</label>',
        '<input name="usdt_trc20" value="',
        field("usdt_trc20"),
        '">',
        '</div>',

        '<div class="field">',
        '<label>USDT BEP20</label>',
        '<input name="usdt_bep20" value="',
        field("usdt_bep20"),
        '">',
        '</div>',

        '<div class="field">',
        '<label>BNB</label>',
        '<input name="bnb_address" value="',
        field("bnb_address"),
        '">',
        '</div>',

        '<div class="field">',
        '<label>TRON</label>',
        '<input name="tron_address" value="',
        field("tron_address"),
        '">',
        '</div>',

        '<button class="btn" type="submit">',
        'Enregistrer',
        '</button>',

        '</form>'
    ])

    return layout(
        "Profil",
        body
    )


# ============================================================
# NOTIFICATIONS
# ============================================================

@app.route("/notifications")
def notifications():

    user, redir = login_required()

    if redir:
        return redir

    rows = db_execute(
        """
        SELECT *
        FROM notifications
        WHERE user_id=%s
        ORDER BY created_at DESC
        LIMIT 50
        """,
        (user["id"],),
        fetchall=True
    )

    db_execute(
        """
        UPDATE notifications
        SET read_at=NOW()
        WHERE user_id=%s
        AND read_at IS NULL
        """,
        (user["id"],),
        commit=True
    )

    items = ''.join(

        '<div class="notice">'

        '<strong>'
        + esc(r["title"])
        + '</strong>'

        '<br>'

        + esc(r["message"])

        '<br>'

        '<span class="small muted">'
        + esc(r["created_at"])
        + '</span>'

        '</div>'

        for r in rows
    )

    return layout(
        "Notifications",
        '<h1>Notifications</h1>'
        +
        (
            items
            or
            '<p class="muted">'
            'Aucune notification.'
            '</p>'
        )
    )


# ============================================================
# CLOSER
# ============================================================

@app.route(
    "/closer/<int:quote_id>"
)
def closer(quote_id):

    user, redir = login_required()

    if redir:
        return redir

    quote = quote_access(
        quote_id,
        user["id"]
    )

    events = db_execute(
        """
        SELECT *
        FROM quote_events
        WHERE quote_id=%s
        ORDER BY created_at DESC
        """,
        (
            quote_id,
        ),
        fetchall=True
    )

    event_text = " ".join(

        (
            e["event_type"]
            + " "
            +
            (
                e["note"]
                or ""
            )
        )

        for e in events
    ).lower()

    if (
        "payment_pending"
        in event_text
        or
        "accepted"
        in event_text
        or
        "signed"
        in event_text
    ):

        score = 90

        advice = (
            "Prospect très chaud : "
            "envoyez immédiatement une confirmation "
            "et finalisez le paiement."
        )

    elif "negotiation" in event_text:

        score = 75

        advice = (
            "Prospect chaud : répondez à l’objection "
            "rapidement et proposez une version "
            "révisée du devis."
        )

    elif "viewed" in event_text:

        score = 55

        advice = (
            "Prospect intéressé : une relance courte "
            "et personnalisée est recommandée."
        )

    else:

        score = 25

        advice = (
            "Prospect peu qualifié : vérifiez le besoin "
            "et proposez une prochaine étape claire."
        )

    return layout(
        "AI Closer",
        ''.join([

            '<div class="card">',

            '<h1>Closer — ',
            esc(quote["quote_number"]),
            '</h1>',

            '<div class="stat">',

            '<span class="muted">',
            'Score prospect',
            '</span>',

            '<b>',
            str(score),
            '/100',
            '</b>',

            '</div>',

            '<h3>Action recommandée</h3>',

            '<p>',
            esc(advice),
            '</p>',

            '<h3>Message suggéré</h3>',

            '<div class="notice">',

            'Bonjour, je reviens vers vous concernant ',
            'le devis ',
            esc(quote["quote_number"]),
            '. Je reste disponible pour répondre ',
            'à vos questions et avancer sur la prochaine étape.',

            '</div>',

            '</div>'
        ])
    )


# ============================================================
# ADMINISTRATION
# ============================================================

def admin_log(
    admin_id,
    action,
    details
):

    db_execute(
        """
        INSERT INTO admin_logs
        (
            admin_id,
            action,
            details
        )
        VALUES
        (%s,%s,%s)
        """,
        (
            admin_id,
            action,
            details
        ),
        commit=True
    )


@app.route("/admin")
def admin():

    admin_user = admin_required()

    users = db_execute(
        """
        SELECT COUNT(*) AS n
        FROM users
        """,
        fetchone=True
    )["n"]

    active = db_execute(
        """
        SELECT COUNT(*) AS n
        FROM subscriptions
        WHERE status='active'
        AND plan_code<>'free'
        """,
        fetchone=True
    )["n"]

    pending_sub = db_execute(
        """
        SELECT COUNT(*) AS n
        FROM subscription_payments
        WHERE status='pending'
        """,
        fetchone=True
    )["n"]

    pending_quote = db_execute(
        """
        SELECT COUNT(*) AS n
        FROM quote_payments
        WHERE status='pending'
        """,
        fetchone=True
    )["n"]

    revenue = db_execute(
        """
        SELECT COALESCE(
            SUM(amount),0
        ) AS n

        FROM subscription_payments

        WHERE status='verified'
        """,
        fetchone=True
    )["n"]

    commissions = db_execute(
        """
        SELECT COALESCE(
            SUM(commission_amount),0
        ) AS n

        FROM quote_payments

        WHERE status='verified'
        """,
        fetchone=True
    )["n"]

    subscription_rows = db_execute(
        """
        SELECT
            p.*,
            u.email,
            u.full_name

        FROM subscription_payments p

        JOIN users u
            ON u.id=p.user_id

        WHERE p.status='pending'

        ORDER BY p.created_at
        """,
        fetchall=True
    )

    quote_rows = db_execute(
        """
        SELECT
            p.*,
            u.email,
            u.full_name,
            q.quote_number

        FROM quote_payments p

        JOIN users u
            ON u.id=p.professional_user_id

        JOIN quotes q
            ON q.id=p.quote_id

        WHERE p.status='pending'

        ORDER BY p.created_at
        """,
        fetchall=True
    )

    subscription_table = ''.join(

        '<tr>'

        '<td>'
        + esc(r["full_name"])
        + '<br>'
        + esc(r["email"])
        + '</td>'

        '<td>'
        + esc(r["plan_code"])
        + '</td>'

        '<td>'
        + money(r["amount"])
        + ' XOF'
        + '</td>'

        '<td>'
        + esc(r["method"])
        + '</td>'

        '<td>'
        + esc(r["transaction_id"])
        + '</td>'

        '<td>'

        + (
            '<a href="/admin/proof/subscription/'
            + str(r["id"])
            + '" target="_blank">Preuve</a> · '
            if r["proof_data"]
            else ""
        )

        + '<a href="/admin/subscription/'
        + str(r["id"])
        + '/valider">Valider</a>'

        + ' · '

        + '<a href="/admin/subscription/'
        + str(r["id"])
        + '/rejeter">Rejeter</a>'

        + '</td>'

        '</tr>'

        for r in subscription_rows
    )

    quote_table = ''.join(

        '<tr>'

        '<td>'
        + esc(r["full_name"])
        + '</td>'

        '<td>'
        + esc(r["quote_number"])
        + '</td>'

        '<td>'
        + money(r["gross_amount"])
        + ' '
        + esc(r["currency"])
        + '</td>'

        '<td>'
        + esc(r["method"])
        + '</td>'

        '<td>'
        + esc(r["transaction_id"])
        + '</td>'

        '<td>'

        + (
            '<a href="/admin/proof/quote/'
            + str(r["id"])
            + '" target="_blank">Preuve</a> · '
            if r["proof_data"]
            else ""
        )

        + '<a href="/admin/quote-payment/'
        + str(r["id"])
        + '/valider">Valider</a>'

        + ' · '

        + '<a href="/admin/quote-payment/'
        + str(r["id"])
        + '/rejeter">Rejeter</a>'

        + '</td>'

        '</tr>'

        for r in quote_rows
    )

    body = ''.join([

        '<h1>Administration</h1>',

        '<div class="stats">',

        '<div class="stat">',
        '<span>Utilisateurs</span>',
        '<b>',
        str(users),
        '</b>',
        '</div>',

        '<div class="stat">',
        '<span>Abonnés payants</span>',
        '<b>',
        str(active),
        '</b>',
        '</div>',

        '<div class="stat">',
        '<span>Paiements abonnement</span>',
        '<b>',
        str(pending_sub),
        '</b>',
        '</div>',

        '<div class="stat">',
        '<span>Paiements devis</span>',
        '<b>',
        str(pending_quote),
        '</b>',
        '</div>',

        '<div class="stat">',
        '<span>CA abonnements</span>',
        '<b>',
        money(revenue),
        ' XOF',
        '</b>',
        '</div>',

        '<div class="stat">',
        '<span>Commissions 2%</span>',
        '<b>',
        money(commissions),
        '</b>',
        '</div>',

        '</div>',

        '<br>',

        '<div class="card">',

        '<h2>Paiements abonnements en attente</h2>',

        '<div class="tablewrap">',

        '<table class="table">',

        '<tr>',
        '<th>Utilisateur</th>',
        '<th>Plan</th>',
        '<th>Montant</th>',
        '<th>Méthode</th>',
        '<th>TXID</th>',
        '<th>Action</th>',
        '</tr>',

        subscription_table
        or
        '<tr>'
        '<td colspan="6">'
        'Aucun paiement en attente.'
        '</td>'
        '</tr>',

        '</table>',

        '</div>',

        '</div>',

        '<br>',

        '<div class="card">',

        '<h2>Paiements de devis en attente</h2>',

        '<div class="tablewrap">',

        '<table class="table">',

        '<tr>',
        '<th>Professionnel</th>',
        '<th>Devis</th>',
        '<th>Montant</th>',
        '<th>Méthode</th>',
        '<th>TXID</th>',
        '<th>Action</th>',
        '</tr>',

        quote_table
        or
        '<tr>'
        '<td colspan="6">'
        'Aucun paiement en attente.'
        '</td>'
        '</tr>',

        '</table>',

        '</div>',

        '</div>'
    ])

    return layout(
        "Administration",
        body
    )


# ============================================================
# VALIDATION ABONNEMENT ADMIN
# ============================================================

@app.route(
    "/admin/subscription/<int:payment_id>/<action>"
)
def admin_subscription_action(
    payment_id,
    action
):

    admin_user = admin_required()

    payment = db_execute(
        """
        SELECT *
        FROM subscription_payments
        WHERE id=%s
        """,
        (
            payment_id,
        ),
        fetchone=True
    )

    if not payment:
        abort(404)

    if action == "valider":

        expires = (
            now_utc()
            +
            timedelta(days=30)
        )

        conn = db_connect()

        try:

            with conn.cursor() as cur:

                cur.execute(
                    """
                    UPDATE subscription_payments

                    SET
                        status='verified',
                        verified_at=NOW(),
                        verified_by=%s

                    WHERE id=%s
                    AND status='pending'
                    """,
                    (
                        admin_user["id"],
                        payment_id
                    )
                )

                cur.execute(
                    """
                    UPDATE subscriptions

                    SET status='expired'

                    WHERE user_id=%s
                    AND status='active'
                    """,
                    (
                        payment["user_id"],
                    )
                )

                cur.execute(
                    """
                    INSERT INTO subscriptions
                    (
                        user_id,
                        plan_code,
                        status,
                        started_at,
                        expires_at,
                        payment_id
                    )
                    VALUES
                    (
                        %s,%s,'active',
                        NOW(),%s,%s
                    )
                    """,
                    (
                        payment["user_id"],
                        payment["plan_code"],
                        expires,
                        payment_id
                    )
                )

            conn.commit()

        finally:
            conn.close()

        notify(
            payment["user_id"],
            "Abonnement activé",
            "Votre plan "
            + payment["plan_code"]
            + " est actif pendant 30 jours."
        )

        admin_log(
            admin_user["id"],
            "subscription_verified",
            str(payment_id)
        )

    elif action == "rejeter":

        db_execute(
            """
            UPDATE subscription_payments

            SET
                status='rejected',
                verified_at=NOW(),
                verified_by=%s,
                rejection_reason=
                'Paiement rejeté par l’administration'

            WHERE id=%s
            AND status='pending'
            """,
            (
                admin_user["id"],
                payment_id
            ),
            commit=True
        )

        notify(
            payment["user_id"],
            "Paiement rejeté",
            "Votre paiement d’abonnement a été rejeté. "
            "Contactez le support."
        )

        admin_log(
            admin_user["id"],
            "subscription_rejected",
            str(payment_id)
        )

    else:

        abort(404)

    return redirect(
        "/admin"
    )


# ============================================================
# VALIDATION PAIEMENT DEVIS ADMIN
# ============================================================

@app.route(
    "/admin/quote-payment/<int:payment_id>/<action>"
)
def admin_quote_payment_action(
    payment_id,
    action
):

    admin_user = admin_required()

    payment = db_execute(
        """
        SELECT *
        FROM quote_payments
        WHERE id=%s
        """,
        (
            payment_id,
        ),
        fetchone=True
    )

    if not payment:
        abort(404)

    quote = db_execute(
        """
        SELECT *
        FROM quotes
        WHERE id=%s
        """,
        (
            payment["quote_id"],
        ),
        fetchone=True
    )

    if action == "valider":

        db_execute(
            """
            UPDATE quote_payments

            SET
                status='verified',
                verified_at=NOW(),
                verified_by=%s

            WHERE id=%s
            AND status='pending'
            """,
            (
                admin_user["id"],
                payment_id
            ),
            commit=True
        )

        db_execute(
            """
            UPDATE quotes

            SET
                status='paid',
                paid_at=NOW()

            WHERE id=%s
            """,
            (
                quote["id"],
            ),
            commit=True
        )

        add_event(
            quote["id"],
            "paid",
            "Paiement vérifié"
        )

        notify(
            quote["user_id"],
            "Paiement vérifié",
            "Le paiement du devis "
            + quote["quote_number"]
            + " a été vérifié."
        )

        admin_log(
            admin_user["id"],
            "quote_payment_verified",
            str(payment_id)
        )

    elif action == "rejeter":

        db_execute(
            """
            UPDATE quote_payments

            SET
                status='rejected',
                verified_at=NOW(),
                verified_by=%s

            WHERE id=%s
            AND status='pending'
            """,
            (
                admin_user["id"],
                payment_id
            ),
            commit=True
        )

        notify(
            quote["user_id"],
            "Paiement rejeté",
            "Le paiement du devis "
            + quote["quote_number"]
            + " a été rejeté."
        )

        admin_log(
            admin_user["id"],
            "quote_payment_rejected",
            str(payment_id)
        )

    else:

        abort(404)

    return redirect(
        "/admin"
    )


# ============================================================
# PREUVES DE PAIEMENT
# ============================================================

@app.route(
    "/admin/proof/subscription/<int:payment_id>"
)
def admin_subscription_proof(
    payment_id
):

    admin_required()

    payment = db_execute(
        """
        SELECT
            proof_data,
            proof_mime,
            proof_filename

        FROM subscription_payments

        WHERE id=%s
        """,
        (
            payment_id,
        ),
        fetchone=True
    )

    if (
        not payment
        or not payment["proof_data"]
    ):
        abort(404)

    return send_file(
        BytesIO(
            bytes(
                payment["proof_data"]
            )
        ),
        mimetype=(
            payment["proof_mime"]
            or
            "application/octet-stream"
        ),
        download_name=(
            payment["proof_filename"]
            or
            "proof"
        )
    )


@app.route(
    "/admin/proof/quote/<int:payment_id>"
)
def admin_quote_proof(
    payment_id
):

    admin_required()

    payment = db_execute(
        """
        SELECT
            proof_data,
            proof_mime,
            proof_filename

        FROM quote_payments

        WHERE id=%s
        """,
        (
            payment_id,
        ),
        fetchone=True
    )

    if (
        not payment
        or not payment["proof_data"]
    ):
        abort(404)

    return send_file(
        BytesIO(
            bytes(
                payment["proof_data"]
            )
        ),
        mimetype=(
            payment["proof_mime"]
            or
            "application/octet-stream"
        ),
        download_name=(
            payment["proof_filename"]
            or
            "proof"
        )
    )


# ============================================================
# UTILISATEURS ADMIN
# ============================================================

@app.route("/admin/users")
def admin_users():

    admin_required()

    rows = db_execute(
        """
        SELECT
            id,
            email,
            full_name,
            role,
            company_name,
            active,
            created_at

        FROM users

        ORDER BY created_at DESC
        """,
        fetchall=True
    )

    html = ''.join(

        '<tr>'

        '<td>'
        + str(r["id"])
        + '</td>'

        '<td>'
        + esc(r["full_name"])
        + '<br>'
        + esc(r["email"])
        + '</td>'

        '<td>'
        + esc(r["role"])
        + '</td>'

        '<td>'
        + (
            "Actif"
            if r["active"]
            else
            "Suspendu"
        )
        + '</td>'

        '<td>'

        '<a href="/admin/user/'
        + str(r["id"])
        + '/toggle">',
        'Changer',
        '</a>',

        '</td>'

        '</tr>'

        for r in rows
    )

    body = ''.join([

        '<div class="card">',

        '<h1>Utilisateurs</h1>',

        '<div class="tablewrap">',

        '<table class="table">',

        '<tr>',
        '<th>ID</th>',
        '<th>Compte</th>',
        '<th>Rôle</th>',
        '<th>État</th>',
        '<th></th>',
        '</tr>',

        html,

        '</table>',

        '</div>',

        '</div>'
    ])

    return layout(
        "Utilisateurs",
        body
    )


@app.route(
    "/admin/user/<int:user_id>/toggle"
)
def admin_toggle_user(user_id):

    admin_user = admin_required()

    if user_id == admin_user["id"]:
        return redirect(
            "/admin/users"
        )

    db_execute(
        """
        UPDATE users
        SET active=NOT active
        WHERE id=%s
        """,
        (
            user_id,
        ),
        commit=True
    )

    admin_log(
        admin_user["id"],
        "user_toggle",
        str(user_id)
    )

    return redirect(
        "/admin/users"
    )


# ============================================================
# ERREURS
# ============================================================

@app.errorhandler(413)
def too_large(error):

    return (
        layout(
            "Fichier trop volumineux",
            '<div class="card">'
            '<h1>Fichier trop volumineux</h1>'
            '<p>'
            'La taille maximale est de 3 Mo.'
            '</p>'
            '</div>'
        ),
        413
    )


@app.errorhandler(403)
def forbidden(error):

    return (
        layout(
            "Accès interdit",
            '<div class="card">'
            '<h1>403</h1>'
            '<p>Accès interdit.</p>'
            '</div>'
        ),
        403
    )


@app.errorhandler(404)
def not_found(error):

    return (
        layout(
            "Page introuvable",
            '<div class="card">'
            '<h1>404</h1>'
            '<p>Cette page n’existe pas.</p>'
            '<a class="btn" href="/">'
            'Accueil'
            '</a>'
            '</div>'
        ),
        404
    )


# ============================================================
# LANCEMENT LOCAL
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            "5000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
