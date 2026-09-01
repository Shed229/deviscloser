from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from datetime import datetime, timedelta
import os

# Devis Closer - Complete Flask Application v18.1 FIX APP
# VERSION: v18.1-FIX-APP
# SLOGAN: Devis Closer — Faites de vos devis des contrats.

from flask import Flask
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'deviscloser_secret_2024_change_me')

# --- Configuration CONSTANTS ---
SLOGAN = 'Devis Closer — Faites de vos devis des contrats.'
VERSION = 'v18.1-FIX-APP'

# Country codes for select
COUNTRY_CODES = [
    ('FR', '+33', 'France'),
    ('BE', '+32', 'Belgique'),
    ('CH', '+41', 'Suisse'),
    ('CA', '+1', 'Canada'),
    ('LU', '+352', 'Luxembourg'),
    ('MA', '+212', 'Maroc'),
    ('SN', '+221', 'Sénégal'),
    ('CI', '+225', 'Côte d’Ivoire'),
    ('CM', '+237', 'Cameroun'),
    ('TN', '+216', 'Tunisie'),
    ('DZ', '+213', 'Algérie'),
    ('GB', '+44', 'Royaume-Uni'),
    ('DE', '+49', 'Allemagne'),
    ('ES', '+34', 'Espagne'),
    ('IT', '+39', 'Italie'),
]

# In-memory storage for demo purposes
DEVIS_DB = {}
USER_DB = {
    'owner': {'password': 'owner123', 'role': 'owner', 'name': 'Propriétaire'},
    'client': {'password': 'client123', 'role': 'client', 'name': 'Client Example'},
}
NEXT_ID = 1

# --- Helper Functions ---
def is_owner():
    """Return True if current user is the owner."""
    return session.get('role') == 'owner'

def is_authenticated():
    """Return True if user is authenticated."""
    return 'username' in session

def get_user():
    """Return current user info or None."""
    uname = session.get('username')
    return USER_DB.get(uname) if uname else None

# --- Routes ---

@app.route('/')
def index():
    """Homepage with SEO metadata, slogan and single FAQ."""
    meta = {
        'title': f'{SLOGAN} | Devis Closer {VERSION}',
        'description': 'Transformez vos devis en contrats signés rapidement. Solution simple pour propriétaires et clients. Suivi, livraison et validation en toute transparence.'
    }
    return render_template('index.html', slogan=SLOGAN, version=VERSION, meta=meta, faq=SINGLE_FAQ)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login route for owner or client."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = USER_DB.get(username)
        if user and user['password'] == password:
            session['username'] = username
            session['role'] = user['role']
            session['name'] = user['name']
            flash(f"Bienvenue {user['name']} !", 'success')
            return redirect(url_for('dashboard'))
        flash("Identifiants invalides.", 'danger')
    return render_template('login.html', meta={'title': 'Connexion | Devis Closer'})

@app.route('/logout')
def logout():
    """Logout and clear session."""
    session.clear()
    flash("Vous avez été déconnecté.", 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    """Dashboard shows devis list depending on role."""
    if not is_authenticated():
        return redirect(url_for('login'))
    user = get_user()
    if is_owner():
        devis_list = list(DEVIS_DB.values())
    else:
        devis_list = [d for d in DEVIS_DB.values() if d.get('client') == session.get('username')]
    return render_template('dashboard.html', devis_list=devis_list, user=user, is_owner=is_owner())

@app.route('/create', methods=['GET', 'POST'])
def create_devis():
    """Create a new devis. Only owner can create."""
    if not is_authenticated() or not is_owner():
        abort(403)
    if request.method == 'POST':
        global NEXT_ID
        title = request.form.get('title', '').strip()
        client = request.form.get('client', '').strip()
        amount = request.form.get('amount', '').strip()
        delivery_date = request.form.get('delivery_date', '').strip()
        country_code = request.form.get('country_code', 'FR')
        cgu = request.form.get('cgu') == 'on'
        if not all([title, client, amount, delivery_date]) or not cgu:
            flash("Tous les champs sont obligatoires et les CGU doivent être acceptées.", 'danger')
            return render_template('create.html', countries=COUNTRY_CODES, meta={'title': 'Créer un devis | Devis Closer'})
        devis = {
            'id': NEXT_ID,
            'title': title,
            'client': client,
            'amount': amount,
            'delivery_date': delivery_date,
            'country_code': country_code,
            'status': 'draft',
            'owner': session.get('username'),
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'cgu_accepted': True,
        }
        DEVIS_DB[NEXT_ID] = devis
        NEXT_ID += 1
        flash("Devis créé avec succès !", 'success')
        return redirect(url_for('dashboard'))
    tomorrow = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    return render_template('create.html', countries=COUNTRY_CODES, default_date=tomorrow, meta={'title': 'Créer un devis | Devis Closer'})

@app.route('/devis/<int:devis_id>')
def devis_detail(devis_id):
    """Detail view with owner vs client logic."""
    if not is_authenticated():
        return redirect(url_for('login'))
    devis = DEVIS_DB.get(devis_id)
    if not devis:
        abort(404)
    user_role = session.get('role')
    username = session.get('username')
    # Access control: owner can see all, client only theirs
    if user_role != 'owner' and devis.get('client') != username:
        abort(403)
    return render_template('devis.html', devis=devis, is_owner=is_owner(), meta={'title': f"Devis #{devis_id} | Devis Closer"})

@app.route('/devis/<int:devis_id>/update_status', methods=['POST'])
def update_status(devis_id):
    """Update devis status: client can sign, owner can validate or deliver."""
    if not is_authenticated():
        abort(403)
    devis = DEVIS_DB.get(devis_id)
    if not devis:
        abort(404)
    new_status = request.form.get('status')
    if is_owner():
        if new_status in ['validated', 'delivered', 'cancelled']:
            devis['status'] = new_status
            flash(f"Statut mis à jour: {new_status}.", 'success')
    else:
        if new_status == 'signed' and devis.get('client') == session.get('username'):
            if devis['status'] == 'validated':
                devis['status'] = 'signed'
                flash("Devis signé par le client.", 'success')
            else:
                flash("Le devis doit être validé par le propriétaire avant signature.", 'warning')
    return redirect(url_for('devis_detail', devis_id=devis_id))

# --- Single FAQ Content ---
SINGLE_FAQ = {
    'question': "Comment transformer mon devis en contrat signé ?",
    'answer': "Une fois le devis créé par le propriétaire et validé, le client peut le signer en un clic. La signature enregistrée vaut acceptation contractuelle, conforme aux CGU acceptées lors de la création. La date de livraison est suivie jusqu'à la livraison finale."
}

# --- Template definitions as strings for self-contained app ---
from flask import render_template_string

BASE_HTML = """
<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ meta.title if meta else 'Devis Closer' }}</title>
<meta name="description" content="{{ meta.description if meta and meta.description else slogan }}">
<meta name="robots" content="index,follow">
<meta property="og:title" content="{{ meta.title if meta else SLOGAN }}">
<meta property="og:description" content="{{ meta.description if meta and meta.description else slogan }}">
<meta property="og:type" content="website">
<style>
*{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;}
body{background:#f5f7fa;color:#1a2333;line-height:1.6;}
header{background:#0b3d66;color:#fff;padding:1rem 2rem;display:flex;justify-content:space-between;align-items:center;}
header a{color:#fff;text-decoration:none;margin:0 .75rem;font-weight:500;}
.container{max-width:1100px;margin:2rem auto;padding:0 1rem;}
.card{background:#fff;border-radius:10px;padding:1.5rem;box-shadow:0 4px 12px rgba(0,0,0,.08);margin-bottom:1.5rem;}
.btn{display:inline-block;padding:.6rem 1.2rem;background:#0b3d66;color:#fff;border:none;border-radius:6px;text-decoration:none;cursor:pointer;font-weight:600;}
.btn:hover{background:#092f4f;}
.btn.secondary{background:#6c757d;}
.badge{display:inline-block;padding:.25rem .6rem;border-radius:4px;background:#e7f1ff;color:#0b3d66;font-size:.85rem;font-weight:600;}
.form-group{margin-bottom:1rem;}
label{display:block;margin-bottom:.4rem;font-weight:600;}
input,select,textarea{width:100%;padding:.6rem;border:1px solid #cbd5e1;border-radius:6px;font-size:1rem;}
.flash{padding:.75rem 1rem;border-radius:6px;margin-bottom:1rem;}
.flash.success{background:#d1fae5;color:#065f46;}
.flash.danger{background:#fee2e2;color:#991b1b;}
.flash.info{background:#dbeafe;color:#1e40af;}
.flash.warning{background:#fef3c7;color:#92400e;}
footer{text-align:center;padding:2rem;color:#6b7280;font-size:.9rem;}
table{width:100%;border-collapse:collapse;}
th,td{padding:.75rem;border-bottom:1px solid #e5e7eb;text-align:left;}
.checkbox{display:flex;align-items:center;gap:.5rem;}
</style>
</head>
<body>
<header>
  <div><strong>Devis Closer</strong> <span class="badge">{{ VERSION }}</span></div>
  <nav>
    <a href="{{ url_for('index') }}">Accueil</a>
    {% if is_authenticated() %}<a href="{{ url_for('dashboard') }}">Tableau de bord</a>
    {% if is_owner() %}<a href="{{ url_for('create_devis') }}">Créer un devis</a>{% endif %}
    <a href="{{ url_for('logout') }}">Déconnexion</a>
    {% else %}<a href="{{ url_for('login') }}">Connexion</a>{% endif %}
  </nav>
</header>
<div class="container">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for cat, msg in messages %}
        <div class="flash {{cat}}">{{ msg }}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}
  {{ content|safe }}
</div>
<footer>
  <p>{{ SLOGAN }} • {{ VERSION }} • © 2024 Devis Closer — Tous droits réservés</p>
</footer>
</body>
</html>
"""

def render_template(name, **ctx):
    templates = {
        'index.html': """
{% set content = '<div class="card"><h1 style="margin-bottom:.5rem;">' + slogan + '</h1><p style="color:#475569;margin-bottom:1rem;">La plateforme qui transforme vos devis en contrats signés, en toute simplicité. Suivi client, validation propriétaire et historique complet.</p><a class="btn" href="'+url_for('dashboard')+'">Accéder au tableau de bord</a><a class="btn secondary" style="margin-left:.5rem;" href="'+url_for('login')+'">Se connecter</a></div><div class="card"><h2>FAQ</h2><h3 style="margin-top:1rem;">'+ faq.question +'</h3><p style="margin-top:.5rem;color:#374151;">'+ faq.answer +'</p></div><div class="card"><h2>Pourquoi Devis Closer ?</h2><ul style="margin-left:1.2rem;margin-top:.5rem;"><li>Gestion des rôles: Propriétaire vs Client</li><li>Date de livraison et suivi par pays</li><li>Acceptation des CGU obligatoire</li><li>Statuts: brouillon → validé → signé → livré</li></ul></div>' %}
""" + BASE_HTML,
        'login.html': """
{% set content = '<div class="card" style="max-width:480px;margin:2rem auto;"><h2>Connexion</h2><form method="post"><div class="form-group"><label>Nom d\'utilisateur</label><input type="text" name="username" placeholder="owner ou client" required></div><div class="form-group"><label>Mot de passe</label><input type="password" name="password" placeholder="owner123 ou client123" required></div><button class="btn" type="submit">Se connecter</button></form><p style="margin-top:1rem;font-size:.9rem;color:#6b7280;">Comptes démo: owner / owner123 — client / client123</p></div>' %}
""" + BASE_HTML,
        'dashboard.html': """
{% set list_html = '' %}
{% if devis_list %}
{% set list_html = '<table><thead><tr><th>ID</th><th>Titre</th><th>Client</th><th>Montant</th><th>Livraison</th><th>Statut</th><th>Action</th></tr></thead><tbody>' %}
{% for d in devis_list %}
{% set list_html = list_html + '<tr><td>#' + d.id|string + '</td><td>' + d.title + '</td><td>' + d.client + '</td><td>' + d.amount + ' €</td><td>' + d.delivery_date + '</td><td><span class="badge">' + d.status + '</span></td><td><a class="btn secondary" href="'+url_for('devis_detail', devis_id=d.id)+'">Voir</a></td></tr>' %}
{% endfor %}
{% set list_html = list_html + '</tbody></table>' %}
{% else %}
{% set list_html = '<p>Aucun devis pour le moment.</p>' %}
{% endif %}
{% set content = '<div class="card"><h2>Tableau de bord — ' + get_user().name + ' (' + get_user().role + ')</h2><p style="color:#475569;">' + ('Vous gérez tous les devis.' if is_owner() else 'Vos devis reçus.') + '</p>' + list_html + '</div>' %}
""" + BASE_HTML,
        'create.html': """
{% set content = '<div class="card" style="max-width:700px;margin:2rem auto;"><h2>Créer un nouveau devis</h2><form method="post"><div class="form-group"><label>Titre du devis</label><input type="text" name="title" placeholder="Ex: Site web vitrine" required></div><div class="form-group"><label>Client</label><input type="text" name="client" placeholder="Nom d\'utilisateur client" required></div><div class="form-group"><label>Montant (€)</label><input type="number" name="amount" step="0.01" placeholder="1500.00" required></div><div class="form-group"><label>Date de livraison</label><input type="date" name="delivery_date" value="'+ default_date +'" required></div><div class="form-group"><label>Code pays / Téléphone</label><select name="country_code" required>' %}
{% for code, dial, country in countries %}{% set content = content + '<option value="'+code+'">'+country+' ('+dial+')</option>' %}{% endfor %}
{% set content = content + '</select></div><div class="form-group checkbox"><input type="checkbox" id="cgu" name="cgu" required><label for="cgu">J\'accepte les Conditions Générales d\'Utilisation (CGU)</label></div><button class="btn" type="submit">Créer le devis</button></form></div>' %}
""" + BASE_HTML,
        'devis.html': """
{% set status_desc = {'draft':'Brouillon','validated':'Validé par le propriétaire','signed':'Signé par le client','delivered':'Livré','cancelled':'Annulé'} %}
{% set content = '<div class="card"><h2>Devis #' + devis.id|string + ' — ' + devis.title + '</h2><p><strong>Client:</strong> ' + devis.client + '</p><p><strong>Montant:</strong> ' + devis.amount + ' €</p><p><strong>Date de livraison:</strong> ' + devis.delivery_date + '</p><p><strong>Pays:</strong> ' + devis.country_code + '</p><p><strong>Statut:</strong> <span class="badge">' + devis.status + ' — ' + status_desc.get(devis.status, devis.status) + '</span></p><p><strong>Créé le:</strong> ' + devis.created_at + '</p><p><strong>CGU acceptées:</strong> Oui</p><hr style="margin:1rem 0;">' %}
{% if is_owner() and devis.status in ['draft','validated','delivered','cancelled'] %}
{% set content = content + '<form method="post" action="'+url_for('update_status', devis_id=devis.id)+'"><div class="form-group"><label>Changer le statut (Propriétaire)</label><select name="status"><option value="validated">Valider le devis</option><option value="delivered">Marquer livré</option><option value="cancelled">Annuler</option></select></div><button class="btn" type="submit">Mettre à jour</button></form>' %}
{% elif not is_owner() and devis.status == 'validated' %}
{% set content = content + '<form method="post" action="'+url_for('update_status', devis_id=devis.id)+'"><input type="hidden" name="status" value="signed"><button class="btn" type="submit">Signer le devis</button></form>' %}
{% endif %}
{% set content = content + '</div>' %}
""" + BASE_HTML
    }
    tmpl = templates.get(name)
    if tmpl is None:
        abort(404)
    return render_template_string(tmpl, **ctx)

def render_template_string(tpl, **ctx):
    # This is used by Flask; placeholder
    pass

if __name__ == '__main__':
    app.run(debug=True, port=5000)
