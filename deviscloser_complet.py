# deviscloser_complet.py — v23 PRO FIXED APP — FULL DESIGN
import os
from flask import Flask, render_template_string
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "deviscloser-v23-pro")

SLOGAN = "Devis Closer — Faites de vos devis des contrats."
MOMO = "01 56 85 31 49"
NAME = "Sosthène Hervé EDOH"
VERSION = "v23 PRO FIXED APP"

HTML = """
<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Devis Closer - {{slogan}}</title>
<style>
body{margin:0;font-family:system-ui;background:#0f172a;color:#fff}
header{display:flex;justify-content:space-between;align-items:center;padding:14px 20px;background:#020617;position:sticky;top:0;z-index:9}
nav a{color:#94a3b8;text-decoration:none;margin:0 4px;padding:8px 12px;border-radius:999px;background:#1e293b;font-size:13px}
nav a.active{background:#3b82f6;color:#fff}
.hero{padding:36px 20px;text-align:center;background:linear-gradient(135deg,#1e3a8a,#0f172a)}
.card{background:#1e293b;border-radius:14px;padding:16px;margin:10px;box-shadow:0 4px 12px rgba(0,0,0,.2)}
.btn{background:#3b82f6;color:#fff;padding:10px 18px;border-radius:999px;text-decoration:none;font-weight:700;display:inline-block}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:12px;padding:20px}
footer{padding:18px;text-align:center;color:#64748b;background:#020617;font-size:12px}
</style></head><body>
<header><div><b style="color:#60a5fa">DC</b> Devis Closer <span style="font-size:10px;background:#22c55e;color:#000;padding:3px 8px;border-radius:999px;margin-left:6px">{{version}}</span></div>
<nav><a href="/" class="{{'active' if p=='h' else ''}}">Accueil</a><a href="/abonnement" class="{{'active' if p=='a' else ''}}">Tarifs</a><a href="/health">Santé</a></nav></header>
{{c|safe}}
<footer>© 2024 Devis Closer - {{slogan}}<br>MoMo {{momo}} - {{name}} • {{version}} • Support WhatsApp 7j/7 via 2290156853149</footer>
</body></html>
"""

def render_page(content, p="h"):
    return render_template_string(HTML, c=content, p=p, slogan=SLOGAN, momo=MOMO, name=NAME, version=VERSION)

@app.route("/")
def home():
    c = f"""
    <div class="hero">
    <div style="display:inline-block;background:#7dd3fc;color:#000;padding:4px 10px;border-radius:999px;font-size:12px">{SLOGAN}</div>
    <h1 style="font-size:28px;margin:14px 0 8px">Faites de vos devis des contrats.</h1>
    <p style="color:#cbd5e1;max-width:700px;margin:auto">Passez de devis ignoré à signature en quelques clics. Relances automatiques, envoi WhatsApp, suivi temps réel et IA pour relancer au bon moment.</p>
    <div style="margin:18px"><a class="btn" href="/abonnement">Voir les plans</a> <a class="btn" style="background:#1e293b" href="https://wa.me/2290156853149">Contacter {NAME}</a></div>
    <div class="grid" style="max-width:900px;margin:18px auto">
      <div class="card">WhatsApp intégré<br><small>Envoi direct sur WhatsApp</small></div>
      <div class="card">Relance IA<br><small>Messages générés par IA</small></div>
      <div class="card">Signature électronique<br><small>Contrats signés en ligne</small></div>
      <div class="card">Tableau de bord<br><small>Suivi clair de vos devis</small></div>
    </div>
    </div>
    <div style="padding:10px 20px;max-width:1100px;margin:auto">
    <h2>Tarifs simples, transparents</h2>
    <div class="grid">
      <div class="card"><h3>Free<br><span style="color:#38bdf8">0€</span></h3>✅ 1 devis / mois<br>✅ Signature basique<br>✅ Support communauté<br><br><a class="btn" href="#">Choisir Free</a></div>
      <div class="card" style="border:2px solid #22c55e"><h3>WhatsApp Starter<br><span style="color:#38bdf8">6500 XOF / mois</span></h3>✅ Jusqu'à 50 devis / mois<br>✅ Envoi WhatsApp direct<br>✅ Templates pro<br>✅ Relances manuelles<br><br><a class="btn" href="#">Choisir Starter</a></div>
      <div class="card" style="border:2px solid #a855f7"><h3>Pro ✨<br><span style="color:#a78bfa">15000 XOF / mois</span></h3>✅ Devis illimités<br>✅ Relance IA automatique<br>✅ Analytics avancés & suivi<br>✅ Signature électronique<br>✅ Intégration MoMo Paiement {MOMO}<br><br><a class="btn" style="background:#a855f7" href="#">Choisir Pro</a></div>
    </div>
    <div class="card" style="text-align:center;background:#052e16;border:1px solid #22c55e">
      <b>PAIEMENT MOMO</b><br>MoMo Paiement: {MOMO}<br>{NAME}<br>Email: sosthene.edoh@deviscloser.pro
    </div>
    </div>
    """
    return render_page(c, "h")

@app.route("/abonnement")
def abo():
    c = f"""
    <div style="padding:20px;max-width:900px;margin:auto">
    <h1>Abonnement</h1>
    <div class="grid">
      <div class="card">Free 0 XOF<br>3 devis / mois<br>WhatsApp base<br>Support</div>
      <div class="card">Starter 6500 XOF<br>50 devis<br>Relance IA basique<br>MoMo {MOMO}</div>
      <div class="card">Pro 15000 XOF<br>Illimité<br>Relance IA avancée<br>MoMo + WhatsApp auto</div>
    </div>
    <p>Contact activation: WhatsApp 2290156853149 — {NAME} — MoMo {MOMO}</p>
    </div>
    """
    return render_page(c, "a")

@app.route("/health")
def health():
    return f"OK {VERSION} — {SLOGAN} — MoMo {MOMO} {NAME}", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))import os
from flask import Flask, render_template_string
app = Flask(__name__)
app.secret_key = "deviscloser-v23"
@app.route("/")
def home():
    return render_template_string("<h1>Devis Closer — Faites de vos devis des contrats.</h1><p>MoMo 01 56 85 31 49 — Sosthène Hervé EDOH — v23 PRO FIXED APP</p><a href='/health'>health</a>")
@app.route("/health")
def health():
    return "OK v23-PRO-FIXED"
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
