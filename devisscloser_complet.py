# deviscloser_complet.py v17 FINAL PRO
# Devis Closer — Faites de vos devis des contrats.
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from functools import wraps

SLOGAN = 'Devis Closer — Faites de vos devis des contrats.'
VERSION = 'v17-FINAL-SEO'

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'deviscloser-secret-v17-final-pro')

DB_PATH = os.path.join(os.path.dirname(__file__), 'deviscloser.db')

COUNTRY_CODES = [
    ('+229', 'BJ', 'Bénin'),
    ('+33', 'FR', 'France'),
    ('+1', 'US', 'États-Unis'),
    ('+228', 'TG', 'Togo'),
    ('+225', 'CI', "Côte d'Ivoire"),
    ('+221', 'SN', 'Sénégal'),
    ('+234', 'NG', 'Nigéria'),
    ('+237', 'CM', 'Cameroun'),
]

DEVISES = [
    ('XOF', 'Franc CFA BCEAO'),
    ('EUR', 'Euro'),
    ('USD', 'Dollar US'),
]

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS devis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        client_name TEXT NOT NULL,
        client_email TEXT NOT NULL,
        client_phone TEXT,
        country_code TEXT NOT NULL,
        currency TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        amount REAL NOT NULL,
        delivery_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'draft',
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    conn.commit()
    conn.close()

init_db()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash("Veuillez vous connecter pour accéder à cette page.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.context_processor
def inject_globals():
    return dict(SLOGAN=SLOGAN, VERSION=VERSION, now=datetime.now().year)

@app.route('/')
def home():
    meta_desc = "Devis Closer transforme vos devis en contrats signés. Générez, partagez et faites accepter vos devis avec paiement crypto. Solution simple pour artisans, freelances et PME en Afrique et partout."
    return render_template('home.html', meta_desc=meta_desc)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        cgu = request.form.get('cgu')
        if not all([name, email, password, cgu]):
            flash("Tous les champs sont obligatoires. Vous devez accepter les CGU.", "error")
        else:
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT id FROM users WHERE email=?", (email,))
            if c.fetchone():
                flash("Cet email est déjà enregistré.", "error")
                conn.close()
            else:
                pwd_hash = generate_password_hash(password)
                c.execute("INSERT INTO users (email,password,name,created_at) VALUES (?,?,?,?)",
                          (email, pwd_hash, name, datetime.now().isoformat()))
                conn.commit()
                user_id = c.lastrowid
                conn.close()
                session['user_id'] = user_id
                session['user_name'] = name
                flash("Inscription réussie ! Bienvenue sur Devis Closer.", "success")
                return redirect(url_for('dashboard'))
    return render_template('register.html', country_codes=COUNTRY_CODES)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=?", (email,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            flash("Connexion réussie.", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Email ou mot de passe invalide.", "error")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Vous êtes déconnecté.", "info")
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM devis WHERE user_id=? ORDER BY created_at DESC", (session['user_id'],))
    devis_list = c.fetchall()
    conn.close()
    return render_template('dashboard.html', devis_list=devis_list)

@app.route('/devis/create', methods=['GET','POST'])
@login_required
def devis_create():
    if request.method == 'POST':
        client_name = request.form.get('client_name','').strip()
        client_email = request.form.get('client_email','').strip()
        client_phone = request.form.get('client_phone','').strip()
        country_code = request.form.get('country_code','+229')
        currency = request.form.get('currency','XOF')
        title = request.form.get('title','').strip()
        description = request.form.get('description','').strip()
        amount = request.form.get('amount','0')
        delivery_date = request.form.get('delivery_date','')
        try:
            amount_val = float(amount)
        except ValueError:
            flash("Le montant doit être un nombre valide.", "error")
            return render_template('devis_create.html', country_codes=COUNTRY_CODES, devises=DEVISES, today=date.today().isoformat())
        if not all([client_name, client_email, title, delivery_date]) or amount_val <= 0:
            flash("Veuillez remplir tous les champs obligatoires.", "error")
        else:
            conn = get_db()
            c = conn.cursor()
            c.execute('''INSERT INTO devis (user_id, client_name, client_email, client_phone, country_code, currency, title, description, amount, delivery_date, status, created_at)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                      (session['user_id'], client_name, client_email, client_phone, country_code, currency, title, description, amount_val, delivery_date, 'draft', datetime.now().isoformat()))
            conn.commit()
            devis_id = c.lastrowid
            conn.close()
            flash("Devis créé avec succès !", "success")
            return redirect(url_for('devis_view', devis_id=devis_id))
    today = date.today().isoformat()
    return render_template('devis_create.html', country_codes=COUNTRY_CODES, devises=DEVISES, today=today)

@app.route('/devis/<int:devis_id>')
@login_required
def devis_view(devis_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM devis WHERE id=?", (devis_id,))
    devis = c.fetchone()
    conn.close()
    if not devis:
        flash("Devis introuvable.", "error")
        return redirect(url_for('dashboard'))
    is_owner = session.get('user_id') == devis['user_id']
    return render_template('devis_view.html', devis=devis, is_owner=is_owner, country_codes=COUNTRY_CODES, devises=DEVISES)

@app.route('/devis/<int:devis_id>/accept')
@login_required
def devis_accept(devis_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM devis WHERE id=?", (devis_id,))
    devis = c.fetchone()
    if not devis:
        flash("Devis introuvable.", "error")
        conn.close()
        return redirect(url_for('dashboard'))
    is_owner = session.get('user_id') == devis['user_id']
    if is_owner:
        flash("Vous ne pouvez pas accepter votre propre devis.", "error")
        conn.close()
        return redirect(url_for('devis_view', devis_id=devis_id))
    c.execute("UPDATE devis SET status='accepted' WHERE id=?", (devis_id,))
    conn.commit()
    conn.close()
    flash("Devis accepté et paiement crypto en attente !", "success")
    return redirect(url_for('devis_view', devis_id=devis_id))

@app.route('/settings', methods=['GET','POST'])
@login_required
def settings():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (session['user_id'],))
    user = c.fetchone()
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        if name:
            c.execute("UPDATE users SET name=? WHERE id=?", (name, session['user_id']))
            conn.commit()
            session['user_name'] = name
            flash("Paramètres mis à jour.", "success")
        else:
            flash("Le nom ne peut pas être vide.", "error")
    conn.close()
    return render_template('settings.html', user=user)

@app.route('/faq')
def faq():
    faqs = [
        ("Qu'est-ce que Devis Closer ?", "Devis Closer est une plateforme qui permet de créer des devis professionnels, les partager avec vos clients, et les transformer en contrats acceptés avec paiement crypto."),
        ("Comment accepter un devis ?", "Le client reçoit le lien du devis, consulte les détails, puis clique sur 'Accepter et payer en crypto' pour valider."),
        ("Quels moyens de paiement sont disponibles ?", "Nous proposons le paiement en crypto-monnaie pour finaliser l'acceptation du devis."),
        ("Est-ce sécurisé ?", "Oui, toutes les données sont sécurisées et stockées en base SQLite/PostgreSQL. Les mots de passe sont hashés."),
    ]
    return render_template('faq.html', faqs=faqs)

@app.route('/cgu')
def cgu():
    return render_template('cgu.html')

@app.route('/robots.txt')
def robots_txt():
    content = "User-agent: *\nAllow: /\nSitemap: /sitemap.xml"
    response = make_response(content)
    response.headers["Content-Type"] = "text/plain"
    return response

@app.route('/sitemap.xml')
def sitemap_xml():
    pages = ['/', '/login', '/register', '/faq', '/cgu']
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    base = request.url_root.rstrip('/')
    for p in pages:
        xml.append(f"  <url><loc>{base}{p}</loc></url>")
    xml.append('</urlset>')
    response = make_response("\n".join(xml))
    response.headers["Content-Type"] = "application/xml"
    return response

# --- TEMPLATES AS STRINGS ---
HOME_HTML = '''<!doctype html><html lang="fr"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Devis Closer | {{ SLOGAN }}</title>
<meta name="description" content="{{ meta_desc }}">
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;margin:0;background:#0f172a;color:#e2e8f0}
header{background:#0b1220;padding:14px 20px;display:flex;justify-content:space-between;align-items:center}
header a{color:#e2e8f0;text-decoration:none;margin:0 10px;font-weight:500}
.hero{padding:60px 20px;text-align:center;background:linear-gradient(135deg,#1e293b,#0b1220)}
.hero h1{font-size:2.2rem;margin:0 0 12px;color:#22d3ee}
.hero p{font-size:1.1rem;color:#cbd5e1;max-width:700px;margin:0 auto 20px}
.btn{display:inline-block;padding:12px 22px;background:#22d3ee;color:#0b1220;border-radius:8px;text-decoration:none;font-weight:700}
.container{max-width:1000px;margin:30px auto;padding:0 20px}
footer{background:#0b1220;padding:20px;text-align:center;color:#94a3b8;font-size:.9rem}
.features{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin-top:30px}
.card{background:#1e293b;padding:18px;border-radius:12px;border:1px solid #334155}
</style></head><body>
<header><div><strong>Devis Closer</strong> <small>{{ VERSION }}</small></div>
<nav><a href="/">Accueil</a><a href="/dashboard">Dashboard</a><a href="/faq">FAQ</a><a href="/settings">Paramètres</a>{% if session.user_id %}<a href="/logout">Déconnexion</a>{% else %}<a href="/login">Connexion</a><a href="/register">Inscription</a>{% endif %}</nav></header>
<section class="hero"><h1>{{ SLOGAN }}</h1><p>{{ meta_desc }}</p><a class="btn" href="/devis/create">Créer mon premier devis</a></section>
<div class="container"><div class="features">
<div class="card"><h3>Devis Pro</h3><p>Créez des devis en quelques clics avec pays et devise.</p></div>
<div class="card"><h3>Acceptation Client</h3><p>Votre client accepte et paye en crypto en un clic.</p></div>
<div class="card"><h3>Suivi & Partage</h3><p>Partagez via WhatsApp, Email ou lien. Suivi en temps réel.</p></div>
</div></div>
<footer>© {{ now }} Devis Closer — {{ VERSION }} • <a href="/cgu" style="color:#94a3b8">CGU</a> • <a href="/faq" style="color:#94a3b8">FAQ</a></footer>
</body></html>'''

REGISTER_HTML = '''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Inscription - Devis Closer</title>
<style>body{font-family:system-ui;background:#0f172a;color:#e2e8f0;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}form{background:#1e293b;padding:24px;border-radius:12px;width:380px;border:1px solid #334155}input,select{width:100%;padding:10px;margin:8px 0;border-radius:6px;border:1px solid #334155;background:#0f172a;color:#e2e8f0}button{width:100%;padding:12px;background:#22d3ee;border:none;border-radius:8px;color:#0b1220;font-weight:700;cursor:pointer}.flash{background:#334155;padding:8px;border-radius:6px;margin-bottom:8px}.cgu{display:flex;align-items:center;gap:8px}label{font-size:.9rem}</style></head><body>
<form method="post"><h2>Inscription</h2>{% with messages = get_flashed_messages(with_categories=true) %}{% for cat,msg in messages %}<div class="flash">{{msg}}</div>{% endfor %}{% endwith %}
<input name="name" placeholder="Nom complet" required>
<input name="email" type="email" placeholder="Email" required>
<input name="password" type="password" placeholder="Mot de passe" required>
<div class="cgu"><input type="checkbox" name="cgu" id="cgu" required><label for="cgu">J'accepte les <a href="/cgu" style="color:#22d3ee">CGU</a></label></div>
<button type="submit">S'inscrire</button><p style="font-size:.85rem">Déjà un compte ? <a href="/login" style="color:#22d3ee">Se connecter</a></p></form></body></html>'''

LOGIN_HTML = '''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Connexion - Devis Closer</title>
<style>body{font-family:system-ui;background:#0f172a;color:#e2e8f0;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}form{background:#1e293b;padding:24px;border-radius:12px;width:360px;border:1px solid #334155}input{width:100%;padding:10px;margin:8px 0;border-radius:6px;border:1px solid #334155;background:#0f172a;color:#e2e8f0}button{width:100%;padding:12px;background:#22d3ee;border:none;border-radius:8px;color:#0b1220;font-weight:700;cursor:pointer}.flash{background:#334155;padding:8px;border-radius:6px;margin-bottom:8px}</style></head><body>
<form method="post"><h2>Connexion</h2>{% with messages = get_flashed_messages(with_categories=true) %}{% for cat,msg in messages %}<div class="flash">{{msg}}</div>{% endfor %}{% endwith %}
<input name="email" type="email" placeholder="Email" required>
<input name="password" type="password" placeholder="Mot de passe" required>
<button type="submit">Se connecter</button><p style="font-size:.85rem">Pas de compte ? <a href="/register" style="color:#22d3ee">S'inscrire</a></p></form></body></html>'''

DASHBOARD_HTML = '''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Dashboard - Devis Closer</title>
<style>body{font-family:system-ui;background:#0f172a;color:#e2e8f0;margin:0}header{background:#0b1220;padding:14px 20px;display:flex;justify-content:space-between}header a{color:#e2e8f0;text-decoration:none;margin:0 10px}.container{max-width:1000px;margin:30px auto;padding:0 20px}table{width:100%;border-collapse:collapse;background:#1e293b;border-radius:8px;overflow:hidden}th,td{padding:12px;border-bottom:1px solid #334155;text-align:left}.btn{display:inline-block;padding:8px 14px;background:#22d3ee;color:#0b1220;border-radius:6px;text-decoration:none;font-weight:600}.flash{background:#334155;padding:8px;border-radius:6px;margin-bottom:12px}</style></head><body>
<header><div><strong>Devis Closer</strong></div><nav><a href="/">Accueil</a><a href="/devis/create">+ Nouveau Devis</a><a href="/settings">Paramètres</a><a href="/logout">Déconnexion</a></nav></header>
<div class="container"><h2>Mon Dashboard</h2>{% with messages = get_flashed_messages(with_categories=true) %}{% for cat,msg in messages %}<div class="flash">{{msg}}</div>{% endfor %}{% endwith %}
<a class="btn" href="/devis/create">+ Créer un devis</a><br><br>
<table><tr><th>#</th><th>Titre</th><th>Client</th><th>Montant</th><th>Échéance</th><th>Statut</th><th>Action</th></tr>
{% for d in devis_list %}<tr><td>{{d['id']}}</td><td>{{d['title']}}</td><td>{{d['client_name']}}</td><td>{{d['amount']}} {{d['currency']}}</td><td>{{d['delivery_date']}}</td><td>{{d['status']}}</td><td><a class="btn" href="/devis/{{d['id']}}">Voir</a></td></tr>{% else %}<tr><td colspan="7">Aucun devis pour le moment.</td></tr>{% endfor %}</table></div></body></html>'''

DEVIS_CREATE_HTML = '''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Créer Devis - Devis Closer</title>
<style>body{font-family:system-ui;background:#0f172a;color:#e2e8f0;margin:0}header{background:#0b1220;padding:14px 20px}form{max-width:700px;margin:30px auto;background:#1e293b;padding:24px;border-radius:12px;border:1px solid #334155}input,select,textarea{width:100%;padding:10px;margin:8px 0;border-radius:6px;border:1px solid #334155;background:#0f172a;color:#e2e8f0}button{padding:12px 20px;background:#22d3ee;border:none;border-radius:8px;color:#0b1220;font-weight:700;cursor:pointer}.flash{background:#334155;padding:8px;border-radius:6px;margin-bottom:8px}</style></head><body>
<header><a href="/dashboard" style="color:#e2e8f0;text-decoration:none;">← Retour Dashboard</a></header>
<form method="post"><h2>Nouveau Devis</h2>{% with messages = get_flashed_messages(with_categories=true) %}{% for cat,msg in messages %}<div class="flash">{{msg}}</div>{% endfor %}{% endwith %}
<label>Titre du devis</label><input name="title" placeholder="Ex: Site web vitrine" required>
<label>Description</label><textarea name="description" placeholder="Description des prestations"></textarea>
<label>Nom du client</label><input name="client_name" placeholder="Nom du client" required>
<label>Email du client</label><input name="client_email" type="email" placeholder="client@email.com" required>
<label>Téléphone du client</label><input name="client_phone" placeholder="Téléphone">
<label>Pays / Indicatif</label><select name="country_code">{% for code,c,cc in country_codes %}<option value="{{code}}">{{cc}} ({{code}})</option>{% endfor %}</select>
<label>Devise</label><select name="currency">{% for cur,label in devises %}<option value="{{cur}}">{{cur}} — {{label}}</option>{% endfor %}</select>
<label>Montant</label><input name="amount" type="number" step="0.01" placeholder="100000" required>
<label>Date de livraison</label><input name="delivery_date" type="date" min="{{today}}" required>
<button type="submit">Créer le devis</button></form></body></html>'''

DEVIS_VIEW_HTML = '''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Devis #{{devis['id']}} - Devis Closer</title>
<style>body{font-family:system-ui;background:#0f172a;color:#e2e8f0;margin:0}header{background:#0b1220;padding:14px 20px} .box{max-width:800px;margin:30px auto;background:#1e293b;padding:24px;border-radius:12px;border:1px solid #334155} .badge{padding:4px 10px;border-radius:6px;background:#334155;display:inline-block} .btn{display:inline-block;padding:10px 16px;background:#22d3ee;color:#0b1220;border-radius:8px;text-decoration:none;font-weight:700;margin:5px 5px 5px 0}.flash{background:#334155;padding:8px;border-radius:6px;margin-bottom:8px}.danger{background:#f59e0b}.success{background:#10b981}</style></head><body>
<header><a href="/dashboard" style="color:#e2e8f0;text-decoration:none;">← Retour Dashboard</a></header>
<div class="box"><h2>Devis #{{devis['id']}} — {{devis['title']}}</h2>{% with messages = get_flashed_messages(with_categories=true) %}{% for cat,msg in messages %}<div class="flash">{{msg}}</div>{% endfor %}{% endwith %}
<p><span class="badge">Statut: {{devis['status']}}</span></p>
<p><strong>Client:</strong> {{devis['client_name']}} ({{devis['client_email']}}) — {{devis['country_code']}} {{devis['client_phone']}}</p>
<p><strong>Montant:</strong> {{devis['amount']}} {{devis['currency']}}</p>
<p><strong>Date de livraison:</strong> {{devis['delivery_date']}}</p>
<p><strong>Description:</strong> {{devis['description'] or '-'}}</p>
{% if is_owner %}
<h3>Actions Propriétaire</h3>
<p><a class="btn" href="https://wa.me/{{devis['country_code']}}{{devis['client_phone']}}">Partager via WhatsApp</a>
<a class="btn" href="mailto:{{devis['client_email']}}?subject=Devis {{devis['title']}}">Envoyer par Email</a>
<a class="btn" href="#" onclick="navigator.clipboard.writeText(window.location.href);alert('Lien copié !');">Copier le lien</a></p>
{% else %}
<h3>Action Client</h3>
<p>Vous êtes le client de ce devis. Acceptez et payez en crypto.</p>
<a class="btn success" href="/devis/{{devis['id']}}/accept">Accepter et payer en crypto</a>
{% endif %}
</div></body></html>'''

SETTINGS_HTML = '''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Paramètres - Devis Closer</title>
<style>body{font-family:system-ui;background:#0f172a;color:#e2e8f0;margin:0}header{background:#0b1220;padding:14px 20px}form{max-width:500px;margin:30px auto;background:#1e293b;padding:24px;border-radius:12px;border:1px solid #334155}input{width:100%;padding:10px;margin:8px 0;border-radius:6px;border:1px solid #334155;background:#0f172a;color:#e2e8f0}button{padding:12px 20px;background:#22d3ee;border:none;border-radius:8px;color:#0b1220;font-weight:700;cursor:pointer}.flash{background:#334155;padding:8px;border-radius:6px;margin-bottom:8px}</style></head><body>
<header><a href="/dashboard" style="color:#e2e8f0;text-decoration:none;">← Retour Dashboard</a></header>
<form method="post"><h2>Paramètres</h2>{% with messages = get_flashed_messages(with_categories=true) %}{% for cat,msg in messages %}<div class="flash">{{msg}}</div>{% endfor %}{% endwith %}
<label>Nom</label><input name="name" value="{{user['name']}}" required>
<label>Email</label><input value="{{user['email']}}" disabled>
<button type="submit">Enregistrer</button></form></body></html>'''

FAQ_HTML = '''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>FAQ - Devis Closer</title>
<style>body{font-family:system-ui;background:#0f172a;color:#e2e8f0;margin:0}header{background:#0b1220;padding:14px 20px} .container{max-width:800px;margin:30px auto;padding:20px} details{background:#1e293b;padding:14px;border-radius:8px;margin:10px 0;border:1px solid #334155} summary{font-weight:700;cursor:pointer}</style></head><body>
<header><a href="/" style="color:#e2e8f0;text-decoration:none;">← Accueil</a></header>
<div class="container"><h2>FAQ</h2>{% for q,a in faqs %}<details><summary>{{q}}</summary><p>{{a}}</p></details>{% endfor %}</div></body></html>'''

CGU_HTML = '''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CGU - Devis Closer</title>
<style>body{font-family:system-ui;background:#0f172a;color:#e2e8f0;margin:0}header{background:#0b1220;padding:14px 20px} .container{max-width:800px;margin:30px auto;padding:20px;background:#1e293b;border-radius:12px;border:1px solid #334155}</style></head><body>
<header><a href="/" style="color:#e2e8f0;text-decoration:none;">← Accueil</a></header>
<div class="container"><h2>Conditions Générales d'Utilisation</h2><p>En utilisant Devis Closer, vous acceptez les présentes CGU. La plateforme permet la création de devis et leur paiement en crypto. L'utilisateur est responsable des informations fournies. Les données sont protégées conformément au RGPD.</p><p>Dernière mise à jour : {{ now }}-01-01</p></div></body></html>'''

# Register templates at runtime by overriding jinja loader
from jinja2 import DictLoader
app.jinja_loader = DictLoader({
    'home.html': HOME_HTML,
    'register.html': REGISTER_HTML,
    'login.html': LOGIN_HTML,
    'dashboard.html': DASHBOARD_HTML,
    'devis_create.html': DEVIS_CREATE_HTML,
    'devis_view.html': DEVIS_VIEW_HTML,
    'settings.html': SETTINGS_HTML,
    'faq.html': FAQ_HTML,
    'cgu.html': CGU_HTML,
})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
