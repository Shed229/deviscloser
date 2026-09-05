import os
from flask import Flask, render_template_string, request, redirect
app = Flask(__name__)

# --- CONFIG PAIEMENTS ---
MOMO = "01 56 85 31 49"
MOMO_INT = "2290156853149"
BSC_ADDR = "0xeB3e09b4F53d863dEBb0d49591597741612b6FB1"  # USDT BEP20 + BNB
TRON_ADDR = "THwRRQVtymKPwLdXdc7PmQvmvNaugX2cff"       # USDT TRC20 + TRX
NAME = "Sosthene Herve EDOH"

BASE = """
<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Devis Closer</title>
<style>
body{margin:0;font-family:system-ui;background:#0b1220;color:#e2e8f0}
header{display:flex;justify-content:space-between;align-items:center;padding:14px 18px;background:#020617;flex-wrap:wrap}
.logo{font-weight:900}.logo span{color:#60a5fa}
.nav a{color:#94a3b8;text-decoration:none;margin:5px;font-size:13px;padding:8px 14px;border-radius:999px;background:#1e293b;display:inline-block}
.nav a.primary{background:#3b82f6;color:#fff;font-weight:700}
.nav a.pro{background:#a855f7;color:#fff;font-weight:700}
.hero{text-align:center;padding:50px 20px;background:radial-gradient(circle at top,#1e3a8a,#0b1220)}
.btn{background:#3b82f6;color:#fff;padding:12px 22px;border-radius:999px;text-decoration:none;font-weight:700;display:inline-block;margin:6px;border:0;cursor:pointer}
.btn-dark{background:#1e293b}
.card{background:#151e32;border:1px solid #1e293b;border-radius:16px;padding:20px;margin:10px;word-break:break-all}
.grid{max-width:1100px;margin:auto;display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px;padding:20px}
input,textarea{width:100%;padding:12px;border-radius:10px;border:1px solid #1e293b;background:#0b1220;color:#fff;margin:8px 0;box-sizing:border-box}
.footer{text-align:center;padding:24px;color:#64748b;font-size:12px;background:#020617}
.badge{font-size:11px;background:#22c55e;color:#000;padding:3px 8px;border-radius:999px}
</style></head><body>
<header><div class="logo"><span>DC</span> Devis Closer</div>
<div class="nav">
<a href="/">Accueil</a><a href="/abonnement">Tarifs</a><a href="/dashboard">Mes devis</a>
<a href="/connexion">Connexion</a><a class="primary" href="/inscription">Inscription</a><a class="pro" href="/nouveau-devis">+ Nouveau devis</a>
</div></header>
{{content|safe}}
<div class="footer">
© Devis Closer - Faites de vos devis des contrats.<br>
MoMo {{momo}} - {{name}} - WhatsApp {{momo_int}}<br>
BSC: {{bsc}} | TRON: {{tron}}<br>
Support 7j/7
</div>
</body></html>
"""
def page(c): return render_template_string(BASE, content=c, momo=MOMO, momo_int=MOMO_INT, bsc=BSC_ADDR, tron=TRON_ADDR, name=NAME)

@app.route("/")
def home():
    c = f"""
    <div class="hero"><h1>Faites de vos devis des contrats.</h1>
    <p style="color:#94a3b8;max-width:600px;margin:14px auto">Relance auto WhatsApp, signature, IA. Passez de devis ignore a signe.</p>
    <a class="btn" href="/inscription">Commencer gratuitement</a>
    <a class="btn btn-dark" href="/abonnement">Voir tarifs</a></div>
    <div class="grid">
      <div class="card"><h3>Free</h3><div style="font-size:26px;font-weight:800;color:#38bdf8">0 XOF</div>1 devis/mois<br><br><a class="btn btn-dark" href="/inscription">S'inscrire</a></div>
      <div class="card" style="border-color:#22c55e"><h3>Starter</h3><div style="font-size:26px;font-weight:800;color:#38bdf8">6500 XOF/mois</div>50 devis - WhatsApp<br><br><a class="btn" href="/abonnement">Choisir Starter</a></div>
      <div class="card" style="border-color:#a855f7"><h3>Pro <span class="badge">POPULAIRE</span></h3><div style="font-size:26px;font-weight:800;color:#c084fc">15000 XOF/mois</div>Illimite + IA<br><br><a class="btn" style="background:#a855f7" href="/abonnement">Choisir Pro</a></div>
    </div>
    """
    return page(c)

@app.route("/inscription", methods=["GET","POST"])
def ins():
    if request.method=="POST": return redirect("/dashboard")
    return page("""<div style="max-width:420px;margin:40px auto" class="card"><h2>Inscription</h2><form method="post"><input name="nom" placeholder="Nom complet - Sosthene Herve EDOH" required><input name="email" placeholder="Email" required><input name="tel" placeholder="WhatsApp" required><input type="password" placeholder="Mot de passe" required><button class="btn" style="width:100%">Creer mon compte</button></form><p><a href="/connexion" style="color:#60a5fa">Deja compte ? Connexion</a></p></div>""")

@app.route("/connexion", methods=["GET","POST"])
def conn():
    if request.method=="POST": return redirect("/dashboard")
    return page("""<div style="max-width:420px;margin:40px auto" class="card"><h2>Connexion</h2><form method="post"><input placeholder="Email" required><input type="password" placeholder="Mot de passe" required><button class="btn" style="width:100%">Se connecter</button></form></div>""")

@app.route("/dashboard")
def dash():
    return page("""<div style="max-width:1100px;margin:auto;padding:20px"><h2>Mes devis</h2><div class="grid"><div class="card">Devis #001 - 150 000 XOF - Envoye - <a class="btn" href="https://wa.me/2290156853149">Relancer WhatsApp</a></div><div class="card">Plan: Free - Passez Pro pour illimite<br><a class="btn" href="/abonnement">Voir abonnement</a></div></div><a class="btn" href="/nouveau-devis">+ Nouveau devis</a></div>""")

@app.route("/nouveau-devis", methods=["GET","POST"])
def nouveau():
    if request.method=="POST": return redirect("/dashboard")
    return page("""<div style="max-width:600px;margin:30px auto" class="card"><h2>Nouveau devis</h2><form method="post"><input placeholder="Nom client"><input placeholder="WhatsApp client"><textarea placeholder="Description"></textarea><input placeholder="Montant XOF"><button class="btn" style="width:100%">Generer et envoyer</button></form></div>""")

@app.route("/abonnement")
def abo():
    c = f"""
    <div style="max-width:1000px;margin:30px auto;padding:20px">
    <h1>Tarifs et Paiement</h1>
    <div class="grid">
      <div class="card"><h3>Free</h3>0 XOF - 1 devis/mois<br><a class="btn btn-dark" href="/inscription">Commencer</a></div>
      <div class="card"><h3>Starter 6500 XOF</h3>50 devis/mois<br><a class="btn" href="/inscription">Activer Starter</a></div>
      <div class="card" style="border-color:#a855f7"><h3>Pro 15000 XOF</h3>Illimite + IA<br><a class="btn" style="background:#a855f7" href="/inscription">Activer Pro</a></div>
    </div>
    <div class="card" style="background:#0f1f15;border-color:#22c55e"><h3 style="text-align:center">PAYER MAINTENANT - Activation automatique apres preuve</h3>
    <b>1. MoMo Bénin:</b><br>Numero: {MOMO} ({MOMO_INT})<br>Nom: {NAME}<br><br>
    <b>2. USDT BEP20 + BNB (BSC):</b><br>Adresse: {BSC_ADDR}<br>Reseau: BSC BEP20 - Metamask / Trust Wallet<br><br>
    <b>3. USDT TRC20 + TRX (Tron):</b><br>Adresse: {TRON_ADDR}<br>Reseau: TRON TRC20 - TronLink / Trust Wallet<br><br>
    <p style="font-size:13px;color:#94a3b8">Apres paiement, envoyez capture + TXID sur WhatsApp {MOMO_INT} pour activation en 5 min.</p>
    <a class="btn" href="https://wa.me/{MOMO_INT}?text=Preuve%20paiement%20Devis%20Closer">Envoyer preuve sur WhatsApp</a>
    </div>
    </div>
    """
    return page(c)

@app.route("/health")
def health(): return "OK v26 PRO - MoMo + BSC + TRON - Sosthene EDOH", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
