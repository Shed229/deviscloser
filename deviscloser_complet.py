import os
from flask import Flask, render_template_string
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "deviscloser-v23-pro")

SLOGAN = "Devis Closer - Faites de vos devis des contrats."
MOMO = "01 56 85 31 49"
NAME = "Sosthene Herve EDOH"
VERSION = "v23 PRO FIXED"

PAGE = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Devis Closer</title>
<style>body{margin:0;font-family:system-ui;background:#0f172a;color:#fff}
header{display:flex;justify-content:space-between;padding:14px 20px;background:#020617}
.btn{background:#3b82f6;color:#fff;padding:10px 18px;border-radius:999px;text-decoration:none;display:inline-block}
.card{background:#1e293b;border-radius:12px;padding:16px;margin:10px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:10px;padding:20px}
footer{padding:16px;text-align:center;color:#64748b;background:#020617}</style></head>
<body><header><b>DC Devis Closer {{version}}</b><nav><a href="/" style="color:#fff">Accueil</a> | <a href="/health" style="color:#fff">Sante</a></nav></header>
<div style="text-align:center;padding:30px;background:#1e3a8a"><h1>{{slogan}}</h1><p>Devis ignore a signature en quelques clics. WhatsApp, Relance IA, Signature.</p>
<a class="btn" href="/abonnement">Voir Tarifs</a> <a class="btn" style="background:#1e293b" href="https://wa.me/2290156853149">Contact {{name}}</a></div>
<div class="grid">
<div class="card"><h3>MoMo</h3>{{momo}}<br>{{name}}<br>{{version}}<br>PRO FIXED APP<br>Gunicorn OK</div>
<div class="card"><h3>Free 0 XOF</h3>1 devis/mois<br>Signature basique<br><a class="btn" href="#">Choisir</a></div>
<div class="card" style="border:2px solid #22c55e"><h3>Starter 6500 XOF</h3>50 devis/mois<br>WhatsApp auto<br>Templates pro<br><a class="btn" href="#">Choisir Starter</a></div>
<div class="card" style="border:2px solid #a855f7"><h3>Pro 15000 XOF</h3>Illimite<br>Relance IA auto<br>Analytics<br>Export PDF<br><a class="btn" style="background:#a855f7" href="#">Choisir Pro</a></div>
</div>
<footer>2024 Devis Closer - {{slogan}}<br>MoMo {{momo}} - {{name}} - {{version}} - Support WhatsApp 7j/7</footer>
</body></html>
"""

@app.route("/")
def home():
    return render_template_string(PAGE, slogan=SLOGAN, momo=MOMO, name=NAME, version=VERSION)

@app.route("/abonnement")
def abo():
    return render_template_string(PAGE, slogan=SLOGAN, momo=MOMO, name=NAME, version=VERSION)

@app.route("/health")
def health():
    return f"OK {VERSION} - {MOMO} - {NAME}", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
