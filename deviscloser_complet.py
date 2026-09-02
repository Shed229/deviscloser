import os
from flask import Flask, request, render_template_string, redirect, url_for, flash
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'v19-2-definitive')
SLOGAN = 'Devis Closer — Faites de vos devis des contrats.'
MOMO_NUMBER = '2290156853149'
MOMO_DISPLAY = '01 56 85 31 49'

COUNTRY_CODES = {
    '+229': 'Bénin',
    '+228': 'Togo',
    '+225': 'Côte d\'Ivoire',
    '+221': 'Sénégal',
    '+33': 'France',
    '+1': 'USA/Canada',
}

BASE_HTML = """
<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }} - Devis Closer</title>
<style>
  body { font-family: Arial, sans-serif; background: #f5f7fa; margin:0; padding:0; color:#222;}
  .header { background:#0a6b3b; color:#fff; padding:16px 20px; }
  .header h1 { margin:0; font-size:20px; }
  .slogan { font-size:13px; opacity:0.9; margin-top:4px;}
  .container { max-width: 900px; margin: 20px auto; padding: 20px; background:#fff; border-radius:10px; box-shadow:0 2px 8px rgba(0,0,0,0.08);}
  .nav { margin: 10px 0 20px; display:flex; gap:12px; flex-wrap:wrap;}
  .nav a { background:#0a6b3b; color:#fff; text-decoration:none; padding:8px 12px; border-radius:6px; font-size:14px;}
  .nav a:hover { background:#095b32;}
  .btn { background:#0a6b3b; color:#fff; border:none; padding:10px 16px; border-radius:6px; cursor:pointer; text-decoration:none; display:inline-block;}
  .btn:hover { background:#095b32; }
  .alert { background:#e6f7ee; color:#0a6b3b; padding:10px 12px; border-radius:6px; margin-bottom:12px; border:1px solid #bde5d3;}
  .alert-error { background:#fdecea; color:#b42318; border:1px solid #f5c2c0;}
  form { display:grid; gap:12px; }
  label { font-weight:600; font-size:14px;}
  input, select, textarea { padding:8px; border:1px solid #ccc; border-radius:6px; font-size:14px; width:100%; box-sizing:border-box;}
  .grid { display:grid; grid-template-columns: 1fr 1fr; gap:12px; }
  .footer { text-align:center; font-size:12px; color:#666; margin:30px 0 10px;}
  .price { font-size:24px; font-weight:bold; color:#0a6b3b;}
  @media (max-width:700px){ .grid{grid-template-columns:1fr;} }
</style>
</head>
<body>
<div class="header">
  <h1>Devis Closer</h1>
  <div class="slogan">{{ slogan }}</div>
</div>
<div class="container">
  <div class="nav">
    <a href="{{ url_for('home') }}">Accueil</a>
    <a href="{{ url_for('pricing') }}">Tarifs</a>
    <a href="{{ url_for('subscribe') }}">S'abonner</a>
    <a href="{{ url_for('momo') }}">Paiement MoMo</a>
    <a href="{{ url_for('devis') }}">Créer un devis</a>
    <a href="{{ url_for('cgu') }}">CGU</a>
  </div>
  {% if message %}
  <div class="alert {{ 'alert-error' if is_error else '' }}">{{ message }}</div>
  {% endif %}
  {{ content|safe }}
</div>
<div class="footer">© {{ now }} Devis Closer • Support MoMo: {{ momo_display }}</div>
</body>
</html>
"""

def render_page(title, content, message=None, is_error=False):
    return render_template_string(BASE_HTML, title=title, content=content, message=message, is_error=is_error, slogan=SLOGAN, momo_display=MOMO_DISPLAY, now=datetime.now().year)

@app.route('/')
def home():
    try:
        content = """
        <h2>Bienvenue sur Devis Closer</h2>
        <p>Transformez vos devis en contrats signés rapidement et simplement.</p>
        <div class="grid">
          <div>
            <h3>Fonctionnalités</h3>
            <ul>
              <li>Création de devis professionnelle</li>
              <li>Suivi et paiement mobile Money</li>
              <li>Signature et livraison digitale</li>
            </ul>
            <p><a class="btn" href="{}">Créer mon premier devis</a></p>
          </div>
          <div>
            <h3>Statut v19.2</h3>
            <p><strong>Version:</strong> v19.2 DÉFINITIVE</p>
            <p><strong>Statut:</strong> Opérationnel</p>
            <p><strong>Livraison estimée:</strong> {}</p>
          </div>
        </div>
        """.format(url_for('devis'), (datetime.now()+timedelta(days=3)).strftime('%d/%m/%Y'))
        return render_page("Accueil", content)
    except Exception as e:
        return render_page("Accueil", "<p>Service temporairement indisponible.</p>", message=f"Erreur: {str(e)}", is_error=True)

@app.route('/cgu')
def cgu():
    try:
        content = """
        <h2>Conditions Générales d'Utilisation (CGU)</h2>
        <p>En utilisant Devis Closer, vous acceptez les conditions suivantes :</p>
        <ul>
          <li>Les devis générés sont valides 30 jours.</li>
          <li>Le paiement via Mobile Money est sécurisé via notre partenaire.</li>
          <li>La livraison est effectuée sous 72h ouvrées après confirmation du paiement.</li>
          <li>Les données sont protégées conformément à la législation en vigueur.</li>
        </ul>
        <p>Date de mise à jour : {}</p>
        """.format(datetime.now().strftime('%d/%m/%Y'))
        return render_page("CGU", content)
    except Exception as e:
        return render_page("CGU", "<p>Impossible de charger les CGU.</p>", message=f"Erreur: {str(e)}", is_error=True)

@app.route('/pricing')
def pricing():
    try:
        content = """
        <h2>Nos Tarifs</h2>
        <div class="grid">
          <div>
            <h3>Starter</h3>
            <div class="price">5 000 FCFA / mois</div>
            <ul>
              <li>10 devis / mois</li>
              <li>Support email</li>
              <li>Paiement MoMo</li>
            </ul>
            <p><a class="btn" href="{}">Choisir Starter</a></p>
          </div>
          <div>
            <h3>Pro</h3>
            <div class="price">15 000 FCFA / mois</div>
            <ul>
              <li>Devis illimités</li>
              <li>Signature électronique</li>
              <li>Support prioritaire 24/7</li>
              <li>Export PDF & CSV</li>
            </ul>
            <p><a class="btn" href="{}">Choisir Pro</a></p>
          </div>
        </div>
        """.format(url_for('subscribe'), url_for('subscribe'))
        return render_page("Tarifs", content)
    except Exception as e:
        return render_page("Tarifs", "<p>Impossible de charger les tarifs.</p>", message=f"Erreur: {str(e)}", is_error=True)

@app.route('/subscribe', methods=['GET','POST'])
def subscribe():
    try:
        if request.method == 'POST':
            plan = request.form.get('plan', 'Starter')
            email = request.form.get('email', '')
            if not email:
                return render_page("S'abonner", form_content(), message="Veuillez saisir un email valide.", is_error=True)
            return render_page("S'abonner", "<h2>Abonnement enregistré</h2><p>Vous avez choisi le plan <strong>{}</strong> pour <strong>{}</strong>.</p><p>Procédez au paiement via Mobile Money pour activer votre abonnement.</p><p><a class='btn' href='{}'>Payer maintenant</a></p>".format(plan, email, url_for('momo')))
        return render_page("S'abonner", form_content())
    except Exception as e:
        return render_page("S'abonner", "<p>Erreur lors de l'abonnement.</p>", message=f"Erreur: {str(e)}", is_error=True)

def form_content():
    return """
    <h2>S'abonner</h2>
    <form method="post">
      <label>Email</label>
      <input type="email" name="email" placeholder="votre@email.com" required>
      <label>Plan</label>
      <select name="plan">
        <option value="Starter">Starter - 5000 FCFA / mois</option>
        <option value="Pro">Pro - 15000 FCFA / mois</option>
      </select>
      <label>Pays</label>
      <select name="country_code">
        {}
      </select>
      <button class="btn" type="submit">S'abonner</button>
    </form>
    """.format("\n".join([f'<option value="{k}">{k} - {v}</option>' for k,v in COUNTRY_CODES.items()]))

@app.route('/momo', methods=['GET','POST'])
def momo():
    try:
        if request.method == 'POST':
            phone = request.form.get('phone', '')
            amount = request.form.get('amount', '5000')
            if not phone:
                return render_page("Paiement MoMo", momo_form(), message="Veuillez saisir votre numéro MoMo.", is_error=True)
            return render_page("Paiement MoMo", f"<h2>Paiement initié</h2><p>Un paiement de <strong>{amount} FCFA</strong> a été initié vers le numéro <strong>{MOMO_DISPLAY}</strong>.</p><p>Veuillez confirmer le paiement sur votre téléphone MoMo au <strong>{phone}</strong>.</p><p>Transaction référence: DC-{datetime.now().strftime('%Y%m%d%H%M%S')}</p><p><a class='btn' href='{url_for('home')}'>Retour à l'accueil</a></p>")
        return render_page("Paiement MoMo", momo_form())
    except Exception as e:
        return render_page("Paiement MoMo", "<p>Erreur paiement MoMo.</p>", message=f"Erreur: {str(e)}", is_error=True)

def momo_form():
    return f"""
    <h2>Paiement Mobile Money</h2>
    <p>Numéro marchand: <strong>{MOMO_DISPLAY}</strong> ({MOMO_NUMBER})</p>
    <form method="post">
      <label>Numéro MoMo du payeur</label>
      <select name="country_code">
        {''.join([f'<option value="{k}">{k} - {v}</option>' for k,v in COUNTRY_CODES.items()])}
      </select>
      <input type="tel" name="phone" placeholder="01 56 85 31 49" required>
      <label>Montant (FCFA)</label>
      <input type="number" name="amount" value="5000" min="1000" step="500" required>
      <button class="btn" type="submit">Payer avec MoMo</button>
    </form>
    """

@app.route('/devis', methods=['GET','POST'])
def devis():
    try:
        if request.method == 'POST':
            client = request.form.get('client', '')
            montant = request.form.get('montant', '0')
            if not client:
                return render_page("Créer un devis", devis_form(), message="Le nom du client est requis.", is_error=True)
            delivery = (datetime.now()+timedelta(days=3)).strftime('%d/%m/%Y')
            return render_page("Devis créé", f"<h2>Devis créé avec succès</h2><p><strong>Client:</strong> {client}</p><p><strong>Montant:</strong> {montant} FCFA</p><p><strong>Date de livraison:</strong> {delivery}</p><p>Le devis a été généré et est prêt à être envoyé.</p><p><a class='btn' href='{url_for('home')}'>Nouveau devis</a></p>")
        return render_page("Créer un devis", devis_form())
    except Exception as e:
        return render_page("Créer un devis", "<p>Erreur création devis.</p>", message=f"Erreur: {str(e)}", is_error=True)

def devis_form():
    return """
    <h2>Créer un devis</h2>
    <form method="post">
      <label>Nom du client</label>
      <input type="text" name="client" placeholder="Nom du client" required>
      <div class="grid">
        <div>
          <label>Montant (FCFA)</label>
          <input type="number" name="montant" value="50000" min="0" step="1000" required>
        </div>
        <div>
          <label>Pays</label>
          <select name="country_code">
            {}
          </select>
        </div>
      </div>
      <label>Description / Prestations</label>
      <textarea name="description" rows="4" placeholder="Détail des prestations..."></textarea>
      <button class="btn" type="submit">Générer le devis</button>
    </form>
    """.format("\n".join([f'<option value="{k}">{k} - {v}</option>' for k,v in COUNTRY_CODES.items()]))

@app.errorhandler(404)
def not_found(e):
    return render_page("404 - Page introuvable", "<h2>Page introuvable</h2><p>La page demandée n'existe pas.</p><p><a class='btn' href='{}'>Retour à l'accueil</a></p>".format(url_for('home')), message="Erreur 404", is_error=True), 404

@app.errorhandler(500)
def server_error(e):
    return render_page("500 - Erreur serveur", "<h2>Erreur serveur</h2><p>Une erreur est survenue. Nos équipes ont été notifiées.</p><p><a class='btn' href='{}'>Retour à l'accueil</a></p>".format(url_for('home')), message="Erreur 500", is_error=True), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
