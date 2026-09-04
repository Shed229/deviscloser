import os
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
