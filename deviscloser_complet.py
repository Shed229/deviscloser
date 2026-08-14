
from flask import Flask, request, redirect, session, g
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, secrets, datetime, json, re, urllib.parse, requests

app = Flask(__name__)
app.secret_key = "deviscloser-v6-crypto-2026"

DB = "deviscloser.db"

ADMIN_CONFIG = {
    "momo_number": "2290156853149",
    "momo_name": "SOSTHENE HERVE EDOH",
    "crypto": {
        "BSC_ADDRESS": "0xeB3e09b4F53d863dEBb0d49591597741612b6FB1",
        "TRON_ADDRESS": "THwRRQVtymKPwLdXdc7PmQvmvNaugX2cff",
    },
    "prices": {
        "STARTER": {"momo": 5900, "USDT_BEP20": 10, "USDT_TRC20": 10, "BNB": 0.025, "TRX": 100},
        "PRO": {"momo": 12900, "USDT_BEP20": 22, "USDT_TRC20": 22, "BNB": 0.055, "TRX": 220}
    },
    "BSCSCAN_API_KEY": "",
}

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db = get_db()
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT,
            plan TEXT DEFAULT 'FREE', expiration TEXT,
            momo_number TEXT, momo_name TEXT, usdt_bep20 TEXT, usdt_trc20 TEXT, bnb_address TEXT, trx_address TEXT
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS devis (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, numero TEXT,
            client_name TEXT, client_email TEXT, client_company TEXT, client_country TEXT,
            valid_until TEXT, delai TEXT, modalites TEXT, notes TEXT,
            subtotal REAL, remise REAL, tva REAL, total REAL, acompte REAL,
            items_json TEXT, status TEXT DEFAULT 'Brouillon', views INTEGER DEFAULT 0, created_at TEXT
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, devis_id INTEGER,
            type TEXT, plan TEXT, method TEXT, network TEXT, amount REAL, currency TEXT,
            txid TEXT UNIQUE, status TEXT, created_at TEXT, verified_data TEXT
        )""")
        for col in ["momo_number","momo_name","usdt_bep20","usdt_trc20","bnb_address","trx_address"]:
            try: db.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
            except: pass
        db.commit()

@app.teardown_appcontext
def close_connection(ex): 
    db=getattr(g,'_database',None)
    if db: db.close()

BASE_CSS = '<meta name="viewport" content="width=device-width, initial-scale=1"><script src="https://cdn.tailwindcss.com"></script>'
def layout(content, user=None):
    nav=""
    if user:
        nav=f"""<nav class='bg-white border-b p-3 flex justify-between items-center text-sm sticky top-0 z-10'>
        <b>DevisCloser</b><div class='flex gap-3 items-center'><a href='/dashboard'>Dashboard</a><a href='/settings'>💳 Paiements</a><a href='/pricing'>Tarifs</a><span class='bg-black text-white px-2 py-1 rounded text-xs'>{user['plan']}</span><a href='/logout' class='text-red-500'>Sortir</a></div></nav>"""
    return f"<html><head>{BASE_CSS}<title>DevisCloser</title></head><body class='bg-gray-50'>{nav}<div class='max-w-5xl mx-auto p-4'>{content}</div></body></html>"

def verify_txid(method, network, txid):
    txid=txid.strip()
    db=get_db()
    if db.execute("SELECT * FROM payments WHERE txid=?", (txid,)).fetchone():
        return False, "❌ Cet ID/TXID déjà utilisé !"
    if method=="MOMO":
        if len(txid)<6: return False, "ID MoMo trop court"
        return True, f"✅ MoMo {txid} reçu"
    if network in ["USDT_BEP20","BNB"]:
        if not txid.startswith("0x") or len(txid)!=66:
            return False, f"TXID {network} invalide : 0x + 66 chars"
        return True, f"✅ TX {network} format valide"
    if network in ["USDT_TRC20","TRX"]:
        if len(txid)!=64:
            return False, f"TXID {network} invalide : 64 chars"
        return True, f"✅ TX {network} format valide"
    return False, "Réseau inconnu"

@app.route("/")
def home():
    if 'user_id' in session: return redirect("/dashboard")
    return layout("<div class='text-center mt-20'><h1 class='text-4xl font-bold'>DevisCloser 🚀</h1><p class='mt-3'>Crée ton devis. Encaisse ton acompte. C'est tout.</p><div class='mt-6 flex gap-3 justify-center'><a href='/register' class='bg-black text-white px-6 py-3 rounded-xl'>S'inscrire</a><a href='/login' class='border px-6 py-3 rounded-xl'>Connexion</a></div></div>")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        email=request.form.get("email").lower().strip(); pwd=request.form.get("password")
        db=get_db()
        try:
            db.execute("INSERT INTO users (email,password,plan) VALUES (?,?,?)",(email,generate_password_hash(pwd),"FREE")); db.commit()
            user=db.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone(); session['user_id']=user['id']; return redirect("/dashboard")
        except: return layout("<p>Email déjà utilisé</p><a href='/register'>Retour</a>")
    return layout("<div class='max-w-sm mx-auto bg-white p-6 rounded-2xl mt-20 shadow'><h2 class='text-xl font-bold'>Inscription</h2><form method='POST' class='mt-4'><input name='email' type='email' placeholder='Email' required class='border p-2 rounded w-full'><input name='password' type='password' placeholder='Mot de passe' required class='border p-2 rounded w-full mt-2'><button class='bg-black text-white w-full py-3 rounded-xl mt-4'>Créer</button></form></div>")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form.get("email").lower().strip(); pwd=request.form.get("password")
        db=get_db(); user=db.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
        if user and check_password_hash(user['password'], pwd):
            session['user_id']=user['id']; return redirect("/dashboard")
        return layout("<p>Faux</p>")
    return layout("<div class='max-w-sm mx-auto bg-white p-6 rounded-2xl mt-20 shadow'><h2 class='text-xl font-bold'>Connexion</h2><form method='POST' class='mt-4'><input name='email' type='email' required class='border p-2 rounded w-full'><input name='password' type='password' required class='border p-2 rounded w-full mt-2'><button class='bg-black text-white w-full py-3 rounded-xl mt-4'>Entrer</button></form></div>")

@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    devis=db.execute("SELECT * FROM devis WHERE user_id=? ORDER BY id DESC",(user['id'],)).fetchall()
    return layout(f"<h1 class='text-2xl font-bold'>Dashboard - {user['plan']}</h1><p class='text-sm text-gray-500'>Bienvenue {user['email']}</p><a href='/create' class='inline-block bg-black text-white px-4 py-2 rounded-xl mt-4'>+ Nouveau devis</a><div class='mt-6 bg-white p-4 rounded-xl border'>{len(devis)} devis</div>",user)

@app.route("/logout")
def logout():
    session.clear(); return redirect("/")

@app.route("/pricing")
def pricing():
    return layout("<h1>Tarifs : STARTER 5900F / PRO 12900F - MoMo + USDT BEP20/TRC20 + BNB/TRX</h1>")

init_db()
if __name__=="__main__": app.run(host="0.0.0.0",port=8080)
