# deviscloser_complet.py v22 FAST START
# Optimized for Render cold start: lazy DB init, instant /health, loading screen, all v21.1 features
# Features: Abonnement Free with WhatsApp, Starter Pro with relance IA, no S'abonner/Paiement Momo tabs, Tarifs renamed Abonnement
# SLOGAN: Devis Closer — Faites de vos devis des contrats.
# MOMO_NUMBER: 2290156853149, MOMO_NAME: Sosthène Hervé EDOH
# Features: Mes devis, Inscription/Connexion/Déconnexion with CGU, delivery_date, country +229, is_owner, anti-black-page

import os
import sqlite3
from flask import Flask, g, request, session, redirect, url_for, render_template_string, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "devkey-faststart-v22")

DB_PATH = os.environ.get("DB_PATH", "/tmp/deviscloser.db")

# --- Lazy DB initialization: only on first use, not at import ---
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name TEXT NOT NULL,
        country TEXT DEFAULT '+229',
        is_owner INTEGER DEFAULT 0,
        plan TEXT DEFAULT 'free',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS devis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        client_name TEXT NOT NULL,
        client_phone TEXT,
        description TEXT NOT NULL,
        amount REAL DEFAULT 0,
        delivery_date TEXT,
        status TEXT DEFAULT 'draft',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)
    db.commit()

def ensure_db_initialized():
    # Lazy init: only create tables if they don't exist
    db = get_db()
    cur = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if cur.fetchone() is None:
        init_db()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    db = get_db()
    return db.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()

# --- Constants ---
MOMO_NUMBER = "2290156853149"
MOMO_NAME = "Sosthène Hervé EDOH"
SLOGAN = "Devis Closer — Faites de vos devis des contrats."

BASE_HTML = """
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{{ title or 'Devis Closer' }}</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background:#0b1020;color:#e6e9f2;line-height:1.5}
    .loading-overlay{position:fixed;inset:0;background:#0b1020;display:flex;align-items:center;justify-content:center;flex-direction:column;z-index:9999;transition:opacity .3s ease,visibility .3s ease}
    .loading-overlay.hidden{opacity:0;visibility:hidden}
    .spinner{width:48px;height:48px;border:4px solid #1f2945;border-top:4px solid #4db8ff;border-radius:50%;animation:spin 0.8s linear infinite}
    @keyframes spin{to{transform:rotate(360deg)}}
    .loading-text{margin-top:14px;font-size:14px;color:#89b4fa;letter-spacing:.5px}
    .container{max-width:1100px;margin:0 auto;padding:20px}
    header{background:#121933;border-bottom:1px solid #1f2945;padding:12px 20px;position:sticky;top:0;z-index:10}
    header .nav{display:flex;align-items:center;justify-content:space-between;gap:16px}
    .brand{font-weight:700;font-size:18px;color:#4db8ff;text-decoration:none;display:flex;align-items:center;gap:8px}
    .badge{background:#1f2945;color:#89b4fa;padding:4px 10px;border-radius:12px;font-size:12px;font-weight:600}
    nav a{color:#cbd5e1;text-decoration:none;margin:0 10px;font-size:14px;padding:6px 10px;border-radius:6px;transition:background .2s}
    nav a:hover{background:#1f2945;color:#fff}
    .btn{background:#4db8ff;color:#0b1020;border:none;padding:10px 16px;border-radius:8px;font-weight:600;cursor:pointer;text-decoration:none;display:inline-block;font-size:14px}
    .btn:hover{background:#37a6f5}
    .btn-secondary{background:#1f2945;color:#e6e9f2}
    .btn-secondary:hover{background:#2a375c}
    .card{background:#121933;border:1px solid #1f2945;border-radius:12px;padding:20px;margin:16px 0}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
    h1{font-size:26px;margin-bottom:8px;color:#fff}
    h2{font-size:20px;margin-bottom:12px;color:#e6e9f2}
    .slogan{color:#89b4fa;font-size:14px;margin-bottom:20px}
    .plan{border:1px solid #1f2945;border-radius:12px;padding:16px;background:#0f1630}
    .plan h3{font-size:16px;color:#4db8ff;margin-bottom:8px}
    .plan-free{border-color:#2dd4bf}
    .plan-pro{border-color:#f59e0b}
    ul{list-style:none;padding-left:0}
    ul li{padding:6px 0;padding-left:22px;position:relative;font-size:14px;color:#cbd5e1}
    ul li:before{content:"✓";position:absolute;left:0;color:#2dd4bf}
    .form-group{margin-bottom:14px}
    label{display:block;font-size:13px;margin-bottom:6px;color:#cbd5e1;font-weight:500}
    input,select,textarea{width:100%;padding:10px;border:1px solid #1f2945;border-radius:8px;background:#0f1630;color:#e6e9f2;font-size:14px}
    input:focus,textarea:focus,select:focus{outline:none;border-color:#4db8ff}
    .flash{padding:10px 14px;border-radius:8px;margin:12px 0;font-size:14px}
    .flash-success{background:#0f3b2f;border:1px solid #2dd4bf;color:#2dd4bf}
    .flash-error{background:#3b0f15;border:1px solid #f87171;color:#f87171}
    .table{width:100%;border-collapse:collapse;font-size:14px}
    .table th,.table td{padding:10px;border-bottom:1px solid #1f2945;text-align:left}
    .table th{color:#89b4fa;font-weight:600;font-size:12px;text-transform:uppercase}
    footer{margin-top:40px;padding:20px;text-align:center;color:#64748b;font-size:12px;border-top:1px solid #1f2945}
    .muted{color:#64748b;font-size:12px}
  </style>
</head>
<body>
  <!-- Loading screen for fast start -->
  <div class="loading-overlay" id="loadingOverlay">
    <div class="spinner"></div>
    <div class="loading-text">Démarrage rapide... Chargement des ressources</div>
  </div>

  <header>
    <div class="container nav">
      <a href="{{ url_for('index') }}" class="brand">⚡ Devis Closer <span class="badge">v22 FAST START</span></a>
      <nav>
        <a href="{{ url_for('index') }}">Accueil</a>
        {% if user %}
        <a href="{{ url_for('mes_devis') }}">Mes devis</a>
        <a href="{{ url_for('abonnement') }}">Abonnement</a>
        <a href="{{ url_for('create_devis') }}">Nouveau devis</a>
        <a href="{{ url_for('logout') }}">Déconnexion</a>
        {% else %}
        <a href="{{ url_for('login') }}">Connexion</a>
        <a href="{{ url_for('register') }}">Inscription</a>
        {% endif %}
      </nav>
    </div>
  </header>

  <div class="container">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, msg in messages %}
          <div class="flash flash-{{ 'success' if category=='success' else 'error' }}">{{ msg }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}
    {{ content|safe }}
  </div>

  <footer>
    <div class="container">
      {{ SLOGAN }} • MoMo: {{ MOMO_NAME }} (+{{ MOMO_NUMBER }}) • Pays: +229
      <div class="muted" style="margin-top:6px;">v22 FAST START • Anti-black-page • Chargement optimisé</div>
    </div>
  </footer>

  <script>
    // Loading screen handling: hide once page is ready for fast start UX
    window.addEventListener('load', function() {
      setTimeout(function(){
        const overlay = document.getElementById('loadingOverlay');
        if(overlay){ overlay.classList.add('hidden'); }
      }, 250);
    });
    // Instant hide if cached
    if (document.readyState === 'complete') {
      document.getElementById('loadingOverlay')?.classList.add('hidden');
    }
  </script>
</body>
</html>
"""

HOME_HTML = """
<h1>Bienvenue sur Devis Closer</h1>
<p class="slogan">{{ SLOGAN }}</p>
<div class="grid">
  <div class="card">
    <h2>Transformez vos devis en contrats signés</h2>
    <p class="muted">Créez, envoyez et suivez vos devis en quelques secondes. Optimisé pour un démarrage instantané même après veille Render.</p>
    {% if not user %}
    <div style="margin-top:16px;">
      <a href="{{ url_for('register') }}" class="btn">Commencer maintenant</a>
      <a href="{{ url_for('login') }}" class="btn btn-secondary">Se connecter</a>
    </div>
    {% else %}
    <div style="margin-top:16px;">
      <a href="{{ url_for('create_devis') }}" class="btn">Créer un devis</a>
      <a href="{{ url_for('mes_devis') }}" class="btn btn-secondary">Voir mes devis</a>
    </div>
    {% endif %}
  </div>
  <div class="card">
    <h2>Pourquoi v22 FAST START?</h2>
    <ul>
      <li>Démarrage instantané: initialisation DB différée</li>
      <li>/health disponible immédiatement pour keep-alive</li>
      <li>Écran de chargement optimisé anti-page noire</li>
      <li>Performance optimisée pour Render free tier</li>
    </ul>
  </div>
</div>
"""

ABONNEMENT_HTML = """
<h1>Abonnement</h1>
<p class="slogan">Choisissez votre plan • Tarifs renommés en Abonnement</p>
<div class="grid">
  <div class="plan plan-free">
    <h3>Free - Gratuit</h3>
    <p class="muted">Idéal pour démarrer</p>
    <ul>
      <li>Jusqu'à 5 devis / mois</li>
      <li>Support WhatsApp direct</li>
      <li>Export PDF basique</li>
    </ul>
    <div style="margin-top:12px;">
      <a href="https://wa.me/{{ MOMO_NUMBER }}?text=Bonjour%20{{ MOMO_NAME | replace(' ','%20') }}%2C%20je%20veux%20activer%20le%20plan%20Free%20sur%20Devis%20Closer" target="_blank" class="btn btn-secondary">Contacter via WhatsApp</a>
    </div>
    <p class="muted" style="margin-top:8px;">Contact: {{ MOMO_NAME }} • +{{ MOMO_NUMBER }}</p>
  </div>
  <div class="plan plan-pro">
    <h3>Starter Pro</h3>
    <p class="muted">Relance IA incluse</p>
    <ul>
      <li>Devis illimités</li>
      <li>Relance IA automatique des clients</li>
      <li>Suivi livraison & rappels par email</li>
      <li>Tableau de bord avancé</li>
      <li>Support prioritaire</li>
    </ul>
    <div style="margin-top:12px;">
      <a href="https://wa.me/{{ MOMO_NUMBER }}?text=Bonjour%20{{ MOMO_NAME | replace(' ','%20') }}%2C%20je%20souhaite%20passer%20au%20plan%20Starter%20Pro%20avec%20Relance%20IA" target="_blank" class="btn">Passer au Pro via WhatsApp</a>
    </div>
    <p class="muted" style="margin-top:8px;">Paiement MoMo: {{ MOMO_NAME }} • +{{ MOMO_NUMBER }}</p>
  </div>
</div>
<div class="card">
  <h2>Comment activer Starter Pro?</h2>
  <p class="muted">1. Cliquez sur "Passer au Pro via WhatsApp" pour nous contacter.</p>
  <p class="muted">2. Envoyez le paiement MoMo au {{ MOMO_NUMBER }} au nom de {{ MOMO_NAME }}.</p>
  <p class="muted">3. Nous activons votre plan sous 5 minutes.</p>
</div>
"""

REGISTER_HTML = """
<h1>Inscription</h1>
<div class="card" style="max-width:500px;">
  <form method="post">
    <div class="form-group">
      <label>Nom complet</label>
      <input type="text" name="name" required placeholder="Votre nom">
    </div>
    <div class="form-group">
      <label>Email</label>
      <input type="email" name="email" required placeholder="email@example.com">
    </div>
    <div class="form-group">
      <label>Pays</label>
      <input type="text" name="country" value="+229" required>
    </div>
    <div class="form-group">
      <label>Mot de passe</label>
      <input type="password" name="password" required placeholder="Min 6 caractères">
    </div>
    <div class="form-group">
      <label><input type="checkbox" name="cgu" required style="width:auto;margin-right:6px;"> J'accepte les Conditions Générales d'Utilisation (CGU)</label>
    </div>
    <button class="btn" type="submit">S'inscrire</button>
  </form>
  <p class="muted" style="margin-top:12px;">Déjà un compte? <a href="{{ url_for('login') }}" style="color:#4db8ff;">Se connecter</a></p>
</div>
"""

LOGIN_HTML = """
<h1>Connexion</h1>
<div class="card" style="max-width:500px;">
  <form method="post">
    <div class="form-group">
      <label>Email</label>
      <input type="email" name="email" required placeholder="email@example.com">
    </div>
    <div class="form-group">
      <label>Mot de passe</label>
      <input type="password" name="password" required placeholder="Votre mot de passe">
    </div>
    <button class="btn" type="submit">Se connecter</button>
  </form>
  <p class="muted" style="margin-top:12px;">Pas encore de compte? <a href="{{ url_for('register') }}" style="color:#4db8ff;">S'inscrire</a></p>
</div>
"""

CREATE_DEVIS_HTML = """
<h1>Nouveau devis</h1>
<div class="card" style="max-width:600px;">
  <form method="post">
    <div class="form-group">
      <label>Nom du client</label>
      <input type="text" name="client_name" required placeholder="Nom du client">
    </div>
    <div class="form-group">
      <label>Téléphone client</label>
      <input type="text" name="client_phone" placeholder="+229...">
    </div>
    <div class="form-group">
      <label>Description du devis</label>
      <textarea name="description" rows="4" required placeholder="Détail des prestations, produits..."></textarea>
    </div>
    <div class="form-group">
      <label>Montant (FCFA)</label>
      <input type="number" name="amount" step="100" placeholder="100000">
    </div>
    <div class="form-group">
      <label>Date de livraison</label>
      <input type="date" name="delivery_date">
    </div>
    <button class="btn" type="submit">Créer le devis</button>
  </form>
</div>
"""

MES_DEVIS_HTML = """
<h1>Mes devis</h1>
<div class="card">
  {% if devis_list %}
  <table class="table">
    <thead>
      <tr><th>#</th><th>Client</th><th>Montant</th><th>Livraison</th><th>Statut</th><th>Créé le</th></tr>
    </thead>
    <tbody>
      {% for d in devis_list %}
      <tr>
        <td>{{ d.id }}</td>
        <td>{{ d.client_name }} <div class="muted">{{ d.client_phone or '' }}</div></td>
        <td>{{ "{:,.0f}".format(d.amount) }} FCFA</td>
        <td>{{ d.delivery_date or '-' }}</td>
        <td>{{ d.status }}</td>
        <td>{{ d.created_at }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% else %}
  <p class="muted">Vous n'avez encore aucun devis. <a href="{{ url_for('create_devis') }}" style="color:#4db8ff;">Créer votre premier devis</a></p>
  {% endif %}
</div>
"""

# --- Routes ---

@app.route("/health")
def health():
    # Instant health check for Render keep-alive / uptime monitors
    return jsonify({"status": "ok", "version": "v22_FAST_START", "timestamp": datetime.utcnow().isoformat() + "Z"}), 200

@app.route("/")
def index():
    ensure_db_initialized()
    user = current_user()
    return render_template_string(BASE_HTML, title="Accueil - Devis Closer", content=HOME_HTML, user=user, SLOGAN=SLOGAN, MOMO_NUMBER=MOMO_NUMBER, MOMO_NAME=MOMO_NAME)

@app.route("/abonnement")
def abonnement():
    ensure_db_initialized()
    user = current_user()
    return render_template_string(BASE_HTML, title="Abonnement - Devis Closer", content=ABONNEMENT_HTML, user=user, SLOGAN=SLOGAN, MOMO_NUMBER=MOMO_NUMBER, MOMO_NAME=MOMO_NAME)

@app.route("/register", methods=["GET","POST"])
def register():
    ensure_db_initialized()
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        country = request.form.get("country","+229").strip()
        cgu = request.form.get("cgu")
        if not cgu:
            flash("Vous devez accepter les CGU pour vous inscrire.", "error")
            return render_template_string(BASE_HTML, title="Inscription", content=REGISTER_HTML, user=None, SLOGAN=SLOGAN, MOMO_NUMBER=MOMO_NUMBER, MOMO_NAME=MOMO_NAME)
        if not name or not email or not password:
            flash("Tous les champs sont requis.", "error")
            return render_template_string(BASE_HTML, title="Inscription", content=REGISTER_HTML, user=None, SLOGAN=SLOGAN, MOMO_NUMBER=MOMO_NUMBER, MOMO_NAME=MOMO_NAME)
        db = get_db()
        exists = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if exists:
            flash("Cet email est déjà inscrit.", "error")
            return render_template_string(BASE_HTML, title="Inscription", content=REGISTER_HTML, user=None, SLOGAN=SLOGAN, MOMO_NUMBER=MOMO_NUMBER, MOMO_NAME=MOMO_NAME)
        pwd_hash = generate_password_hash(password)
        # First user is owner
        is_owner = 1 if db.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"] == 0 else 0
        db.execute("INSERT INTO users (name,email,password_hash,country,is_owner) VALUES (?,?,?,?,?)",
                   (name,email,pwd_hash,country,is_owner))
        db.commit()
        uid = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"]
        session["user_id"] = uid
        flash("Inscription réussie! Bienvenue.", "success")
        return redirect(url_for("index"))
    user = current_user()
    return render_template_string(BASE_HTML, title="Inscription - Devis Closer", content=REGISTER_HTML, user=user, SLOGAN=SLOGAN, MOMO_NUMBER=MOMO_NUMBER, MOMO_NAME=MOMO_NAME)

@app.route("/login", methods=["GET","POST"])
def login():
    ensure_db_initialized()
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Identifiants invalides.", "error")
            return render_template_string(BASE_HTML, title="Connexion", content=LOGIN_HTML, user=None, SLOGAN=SLOGAN, MOMO_NUMBER=MOMO_NUMBER, MOMO_NAME=MOMO_NAME)
        session["user_id"] = user["id"]
        flash("Connexion réussie.", "success")
        nextp = request.args.get("next") or url_for("index")
        return redirect(nextp)
    user = current_user()
    return render_template_string(BASE_HTML, title="Connexion - Devis Closer", content=LOGIN_HTML, user=user, SLOGAN=SLOGAN, MOMO_NUMBER=MOMO_NUMBER, MOMO_NAME=MOMO_NAME)

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Vous êtes déconnecté.", "success")
    return redirect(url_for("index"))

@app.route("/devis", methods=["GET"])
@login_required
def mes_devis():
    ensure_db_initialized()
    user = current_user()
    db = get_db()
    devis_list = db.execute("SELECT * FROM devis WHERE user_id=? ORDER BY created_at DESC", (user["id"],)).fetchall()
    return render_template_string(BASE_HTML, title="Mes devis - Devis Closer", content=MES_DEVIS_HTML, user=user, devis_list=devis_list, SLOGAN=SLOGAN, MOMO_NUMBER=MOMO_NUMBER, MOMO_NAME=MOMO_NAME)

@app.route("/devis/new", methods=["GET","POST"])
@login_required
def create_devis():
    ensure_db_initialized()
    user = current_user()
    if request.method == "POST":
        client_name = request.form.get("client_name","").strip()
        client_phone = request.form.get("client_phone","").strip()
        description = request.form.get("description","").strip()
        amount = request.form.get("amount","0").strip()
        delivery_date = request.form.get("delivery_date","").strip()
        if not client_name or not description:
            flash("Nom du client et description requis.", "error")
            return render_template_string(BASE_HTML, title="Nouveau devis", content=CREATE_DEVIS_HTML, user=user, SLOGAN=SLOGAN, MOMO_NUMBER=MOMO_NUMBER, MOMO_NAME=MOMO_NAME)
        try:
            amt = float(amount) if amount else 0.0
        except:
            amt = 0.0
        db = get_db()
        db.execute("INSERT INTO devis (user_id, client_name, client_phone, description, amount, delivery_date) VALUES (?,?,?,?,?,?)",
                   (user["id"], client_name, client_phone, description, amt, delivery_date or None))
        db.commit()
        flash("Devis créé avec succès!", "success")
        return redirect(url_for("mes_devis"))
    return render_template_string(BASE_HTML, title="Nouveau devis - Devis Closer", content=CREATE_DEVIS_HTML, user=user, SLOGAN=SLOGAN, MOMO_NUMBER=MOMO_NUMBER, MOMO_NAME=MOMO_NAME)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
