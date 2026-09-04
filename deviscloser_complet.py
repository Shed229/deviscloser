
import os
from flask import Flask, request, redirect, session, g
from werkzeug.security import generate_password_hash, check_password_hash
import secrets, datetime, json, re, urllib.parse

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "deviscloser-v15-final-2026")
VERSION="v15-FINAL"

DB_URL = os.environ.get("DATABASE_URL", "")
USE_POSTGRES = DB_URL.startswith("postgres")

if USE_POSTGRES:
    import psycopg2, psycopg2.extras
    if DB_URL.startswith("postgres://"):
        DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

ADMIN_CONFIG = {
    "whatsapp": "2290156853149",
    "crypto": {"BSC_ADDRESS": "0xeB3e09b4F53d863dEBb0d49591597741612b6FB1","TRON_ADDRESS": "THwRRQVtymKPwLdXdc7PmQvmvNaugX2cff"},
    "prices": {
        "STARTER": {"USDT_BEP20": 10, "USDT_TRC20": 10, "BNB": 0.025, "TRX": 100},
        "PRO": {"USDT_BEP20": 22, "USDT_TRC20": 22, "BNB": 0.055, "TRX": 220}
    }
}

def fmt(n):
    try:
        n=float(n)
        if n==int(n): return f"{int(n):,}".replace(","," ")
        return f"{n:,.0f}".replace(","," ")
    except: return str(n)

def get_db():
    db=getattr(g,'_database',None)
    if db is None:
        if USE_POSTGRES:
            db=g._database=psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            import sqlite3
            db=g._database=sqlite3.connect("deviscloser.db")
            db.row_factory=sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db=get_db(); cur=db.cursor()
        if USE_POSTGRES:
            cur.execute("""CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, email TEXT UNIQUE, password TEXT, plan TEXT DEFAULT 'FREE', expiration TEXT, momo_number TEXT, usdt_bep20 TEXT, usdt_trc20 TEXT, is_admin INTEGER DEFAULT 0)""")
            cur.execute("""CREATE TABLE IF NOT EXISTS devis (id SERIAL PRIMARY KEY, user_id INTEGER, numero TEXT, client_name TEXT, client_email TEXT, total REAL, acompte REAL, items_json TEXT, status TEXT DEFAULT 'Brouillon', views INTEGER DEFAULT 0, created_at TEXT)""")
            cur.execute("""CREATE TABLE IF NOT EXISTS payments (id SERIAL PRIMARY KEY, user_id INTEGER, devis_id INTEGER, type TEXT, plan TEXT, method TEXT, network TEXT, amount REAL, currency TEXT, txid TEXT UNIQUE, status TEXT, created_at TEXT, verified_data TEXT)""")
        else:
            cur.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT, plan TEXT DEFAULT 'FREE', expiration TEXT, momo_number TEXT, usdt_bep20 TEXT, usdt_trc20 TEXT, is_admin INTEGER DEFAULT 0)""")
            cur.execute("""CREATE TABLE IF NOT EXISTS devis (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, numero TEXT, client_name TEXT, client_email TEXT, total REAL, acompte REAL, items_json TEXT, status TEXT DEFAULT 'Brouillon', views INTEGER DEFAULT 0, created_at TEXT)""")
            cur.execute("""CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, devis_id INTEGER, type TEXT, plan TEXT, method TEXT, network TEXT, amount REAL, currency TEXT, txid TEXT UNIQUE, status TEXT, created_at TEXT, verified_data TEXT)""")
        db.commit()
        try:
            q="UPDATE users SET is_admin=1 WHERE email LIKE %s" if USE_POSTGRES else "UPDATE users SET is_admin=1 WHERE email LIKE ?"
            cur.execute(q, ('%sosthene%',)); db.commit()
        except: pass

@app.teardown_appcontext
def close_connection(ex):
    db=getattr(g,'_database',None)
    if db:
        try: db.close()
        except: pass

BASE_HTML_HEAD = """
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.tailwindcss.com"></script>
<script>tailwind.config={darkMode:'class'}</script>
<style>
.dark body{background:#0a0a0a;color:#eee}
.dark .bg-white{background:#1a1a1a !important;border-color:#333 !important;color:#eee}
.dark .bg-gray-50{background:#0a0a0a !important}
.dark .border{border-color:#333 !important}
</style>
"""

def navbar(user=None):
    if not user:
        return f"""<nav class='bg-white dark:bg-black border-b p-3 flex justify-between items-center sticky top-0 z-50'><b>DevisCloser v15</b><div class='flex gap-2'><button onclick="toggleDark()" class='border px-3 py-1 rounded-full text-xs'>🌙/☀️</button><a href='/login' class='text-sm'>Connexion</a></div></nav>"""
    is_admin = user['is_admin'] if isinstance(user, dict) else user[7]
    admin_link = "<a href='/admin' class='block px-4 py-3 hover:bg-gray-100 rounded-xl'>👑 Admin</a>" if is_admin else ""
    return f"""
    <nav class='bg-white dark:bg-black border-b p-3 flex justify-between items-center sticky top-0 z-50'>
        <div class='flex gap-3 items-center'><button id='menuBtn' class='border p-2 rounded-xl'>☰</button><b>DevisCloser</b></div>
        <div class='flex gap-2 items-center'><button onclick="toggleDark()" class='border px-3 py-1 rounded-full text-xs'>🌙</button><span class='bg-black dark:bg-white dark:text-black text-white px-3 py-1 rounded-full text-xs'>{user['plan'] if isinstance(user,dict) else user[3]}</span><a href='/logout' class='text-red-500 text-xs'>Sortir</a></div>
    </nav>
    <div id='sideMenu' class='fixed inset-0 z-40 hidden'><div class='absolute inset-0 bg-black/40' onclick='toggleMenu()'></div>
        <div class='absolute left-0 top-0 h-full w-72 bg-white dark:bg-zinc-900 shadow-2xl p-4'>
            <div class='flex justify-between'><b>Menu</b><button onclick='toggleMenu()'>✕</button></div>
            <div class='mt-6 space-y-1'>
                <a href='/dashboard' class='block px-4 py-3 rounded-xl hover:bg-gray-100'>📊 Dashboard</a>
                <a href='/create' class='block px-4 py-3 rounded-xl hover:bg-gray-100'>➕ Nouveau devis</a>
                <a href='/abonnement' class='block px-4 py-3 rounded-xl hover:bg-gray-100'>💎 Abonnement Crypto</a>
                <a href='/settings' class='block px-4 py-3 rounded-xl hover:bg-gray-100'>💳 Mes Paiements Crypto</a>
                {admin_link}
            </div>
            <div class='absolute bottom-4 left-4 right-4'><button onclick="toggleDark()" class='border px-3 py-2 rounded-full w-full text-xs'>🌙/☀️ Mode sombre</button></div>
        </div>
    </div>
    <script>
    function toggleMenu(){{document.getElementById('sideMenu').classList.toggle('hidden')}}
    document.getElementById('menuBtn').onclick=toggleMenu;
    function toggleDark(){{document.documentElement.classList.toggle('dark'); localStorage.setItem('theme', document.documentElement.classList.contains('dark')?'dark':'light')}}
    if(localStorage.getItem('theme')==='dark')document.documentElement.classList.add('dark');
    </script>
    """

def footer():
    db_type = "🟢 Postgres Persistant" if USE_POSTGRES else "🔴 SQLite temporaire"
    return f"<footer class='mt-16 border-t bg-white dark:bg-zinc-900 p-8 text-sm'><div class='max-w-5xl mx-auto'><b>DevisCloser v15 - Le devis qui te fait payer.</b><p class='text-xs text-gray-500 mt-2'>{db_type} - 100% Crypto - USDT BEP20/TRC20 + BNB + TRX - Pas de MoMo</p></div></footer>"

def layout(content,user=None):
    return f"<html><head>{BASE_HTML_HEAD}<title>DevisCloser v15</title></head><body class='bg-gray-50 dark:bg-black'>{navbar(user)}<div class='max-w-5xl mx-auto p-4'>{content}</div>{footer()}</body></html>"

def verify_txid(network,txid):
    txid=txid.strip()
    db=get_db(); cur=db.cursor()
    q="SELECT * FROM payments WHERE txid=%s" if USE_POSTGRES else "SELECT * FROM payments WHERE txid=?"
    cur.execute(q,(txid,))
    if cur.fetchone(): return False,"❌ TXID déjà utilisé !","DUPLICATE"
    if network in ["USDT_BEP20","BNB"]:
        if not txid.startswith("0x") or len(txid)!=66: return False,"❌ TXID BEP20/BNB invalide: doit être 0x + 64 caractères hex (66 total)","INVALID"
        return True,"✅ TX valide - En attente vérification manuelle sous 2h","PENDING"
    if network in ["USDT_TRC20","TRX"]:
        if len(txid)!=64: return False,"❌ TXID TRC20/TRX invalide: doit être 64 caractères hex","INVALID"
        return True,"✅ TX valide - En attente vérification","PENDING"
    return False,"Réseau inconnu","INVALID"

@app.route("/")
def home():
    if 'user_id' in session: return redirect("/dashboard")
    return layout("""
    <div class='text-center mt-16 px-4'>
        <h1 class='text-6xl md:text-8xl font-black leading-[0.9]'>Le devis<br>qui te fait<br><span class='bg-black dark:bg-white dark:text-black text-white px-4 rounded-full'>payer.</span></h1>
        <p class='mt-6 text-xl'>Crée ton devis. Envoie le lien. Encaisse en crypto.</p>
        <div class='mt-8 flex gap-4 justify-center'><a href='/register' class='bg-black dark:bg-white dark:text-black text-white px-8 py-4 rounded-full font-bold'>S'inscrire Gratuit</a><a href='/login' class='border-2 px-8 py-4 rounded-full font-bold'>Connexion</a></div>
        <div class='mt-12 grid md:grid-cols-3 gap-4 max-w-4xl mx-auto text-left'><div class='bg-white dark:bg-zinc-900 border p-6 rounded-[24px]'><b>📤 Envoie au client</b><p class='text-sm text-gray-500 mt-2'>Lien WhatsApp + Mail avec bouton Accepter et payer</p></div><div class='bg-white dark:bg-zinc-900 border p-6 rounded-[24px]'><b>💎 100% Crypto</b><p class='text-sm text-gray-500 mt-2'>USDT BEP20/TRC20 + BNB + TRX. Pas de MoMo.</p></div><div class='bg-white dark:bg-zinc-900 border p-6 rounded-[24px]'><b>🌙 Mode sombre</b><p class='text-sm text-gray-500 mt-2'>Pour bosser la nuit</p></div></div>
    </div>
    """)

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        email=request.form.get("email","").lower().strip(); pwd=request.form.get("password","")
        db=get_db(); cur=db.cursor()
        try:
            q="INSERT INTO users (email,password,plan) VALUES (%s,%s,%s)" if USE_POSTGRES else "INSERT INTO users (email,password,plan) VALUES (?,?,?)"
            cur.execute(q,(email,generate_password_hash(pwd),"FREE")); db.commit()
            q2="SELECT * FROM users WHERE email=%s" if USE_POSTGRES else "SELECT * FROM users WHERE email=?"
            cur.execute(q2,(email,)); user=cur.fetchone()
            session['user_id']=user['id'] if isinstance(user,dict) else user[0]
            return redirect("/dashboard")
        except Exception as e:
            return layout(f"<p>Email déjà utilisé</p>")
    return layout("<div class='max-w-sm mx-auto bg-white dark:bg-zinc-900 p-6 rounded-[24px] mt-16 border'><h2 class='text-xl font-bold'>Inscription</h2><form method='POST' class='mt-4 space-y-3'><input name='email' type='email' required class='border p-3 rounded-xl w-full dark:bg-black'><input name='password' type='password' required class='border p-3 rounded-xl w-full dark:bg-black'><button class='bg-black dark:bg-white dark:text-black text-white w-full py-3 rounded-full font-bold'>Créer</button></form></div>")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form.get("email","").lower().strip(); pwd=request.form.get("password","")
        db=get_db(); cur=db.cursor()
        q="SELECT * FROM users WHERE email=%s" if USE_POSTGRES else "SELECT * FROM users WHERE email=?"
        cur.execute(q,(email,)); user=cur.fetchone()
        if user:
            sp=user['password'] if isinstance(user,dict) else user[2]
            if check_password_hash(sp,pwd):
                session['user_id']=user['id'] if isinstance(user,dict) else user[0]
                return redirect("/dashboard")
        return layout(f"<div class='max-w-sm mx-auto bg-white dark:bg-zinc-900 p-8 rounded-[24px] mt-16 border text-center'><h2>❌ Mauvais email/mot de passe</h2><a href='/register' class='block bg-black text-white py-3 rounded-full mt-6'>Créer compte</a></div>")
    return layout("<div class='max-w-sm mx-auto bg-white dark:bg-zinc-900 p-6 rounded-[24px] mt-16 border'><h2 class='text-xl font-bold'>Connexion</h2><form method='POST' class='mt-4 space-y-3'><input name='email' type='email' required class='border p-3 rounded-xl w-full dark:bg-black'><input name='password' type='password' required class='border p-3 rounded-xl w-full dark:bg-black'><button class='bg-black dark:bg-white dark:text-black text-white w-full py-3 rounded-full font-bold'>Se connecter</button></form></div>")

@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); cur=db.cursor()
    q="SELECT * FROM users WHERE id=%s" if USE_POSTGRES else "SELECT * FROM users WHERE id=?"
    cur.execute(q,(session['user_id'],)); user=cur.fetchone()
    q2="SELECT * FROM devis WHERE user_id=%s ORDER BY id DESC" if USE_POSTGRES else "SELECT * FROM devis WHERE user_id=? ORDER BY id DESC"
    cur.execute(q2,(session['user_id'],)); devis=cur.fetchall()
    rows=""
    for d in devis:
        did=d['id'] if isinstance(d,dict) else d[0]
        numero=d['numero'] if isinstance(d,dict) else d[2]
        client=d['client_name'] if isinstance(d,dict) else d[3]
        total=d['total'] if isinstance(d,dict) else d[5]
        status=d['status'] if isinstance(d,dict) else d[7]
        rows+=f"<div class='bg-white dark:bg-zinc-900 p-4 rounded-2xl border flex justify-between items-center'><div><b>{numero}</b> - {client} - {fmt(total)} FCFA<br><span class='text-xs text-gray-500'>{status}</span></div><a href='/devis/{did}' class='bg-black dark:bg-white dark:text-black text-white px-4 py-2 rounded-full text-xs font-bold'>Gérer → Envoyer</a></div>"
    if not rows:
        rows="<div class='bg-white dark:bg-zinc-900 border-2 border-dashed rounded-[32px] p-12 text-center'><div class='text-6xl'>📤</div><h3 class='text-2xl font-bold mt-4'>Aucun devis</h3><p class='text-gray-500'>Crée ton premier devis et envoie le lien à ton client</p><a href='/create' class='inline-block bg-black dark:bg-white dark:text-black text-white px-8 py-4 rounded-full font-bold mt-6'>+ Nouveau devis</a></div>"
    return layout(f"<h1 class='text-3xl font-black'>Dashboard - {user['plan'] if isinstance(user,dict) else user[3]}</h1><div class='mt-8 space-y-3'>{rows}</div><a href='/create' class='fixed bottom-6 left-1/2 -translate-x-1/2 bg-black dark:bg-white dark:text-black text-white px-8 py-4 rounded-full font-bold shadow-2xl md:hidden'>+ Nouveau</a>",user)

@app.route("/create", methods=["GET","POST"])
def create():
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); cur=db.cursor()
    q="SELECT * FROM users WHERE id=%s" if USE_POSTGRES else "SELECT * FROM users WHERE id=?"
    cur.execute(q,(session['user_id'],)); user=cur.fetchone()
    if request.method=="POST":
        numero=f"DV-{secrets.token_hex(3).upper()}"
        services=request.form.getlist("service[]"); qtes=request.form.getlist("qte[]"); pus=request.form.getlist("pu[]")
        items=[]; subtotal=0
        for s,qty,p in zip(services,qtes,pus):
            if not s: continue
            try: qty=float(qty); p=float(p)
            except: qty=1; p=0
            mt=qty*p; subtotal+=mt; items.append({"service":s,"qte":qty,"pu":p,"total":mt})
        total=subtotal; acompte=total*0.5
        qi="INSERT INTO devis (user_id,numero,client_name,client_email,total,acompte,items_json,status,created_at,views) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO devis (user_id,numero,client_name,client_email,total,acompte,items_json,status,created_at,views) VALUES (?,?,?,?,?,?,?,?,?,?)"
        cur.execute(qi,(session['user_id'],numero,request.form.get("client_name"),request.form.get("client_email"),total,acompte,json.dumps(items),"Brouillon",datetime.datetime.now().isoformat(),0))
        db.commit()
        q2="SELECT * FROM devis WHERE numero=%s" if USE_POSTGRES else "SELECT * FROM devis WHERE numero=?"
        cur.execute(q2,(numero,)); d=cur.fetchone()
        did=d['id'] if isinstance(d,dict) else d[0]
        return redirect(f"/devis/{did}")
    return layout("""
    <h1 class='text-2xl font-bold'>+ Nouveau devis</h1>
    <form method="POST" class="mt-6 bg-white dark:bg-zinc-900 p-6 rounded-[24px] border space-y-3 max-w-3xl">
        <div class='grid md:grid-cols-2 gap-3'><input name="client_name" placeholder="Nom client *" required class="border p-3 rounded-xl w-full dark:bg-black"><input name="client_email" placeholder="WhatsApp / Email client *" required class="border p-3 rounded-xl w-full dark:bg-black"></div>
        <div id="items"><div class='grid grid-cols-12 gap-2 bg-gray-50 dark:bg-black p-2 rounded-xl'><div class='col-span-6'><input name="service[]" placeholder="Service" required class="border p-2 rounded w-full dark:bg-zinc-900"></div><div class='col-span-2'><input name="qte[]" type="number" value="1" class="border p-2 rounded w-full dark:bg-zinc-900"></div><div class='col-span-2'><input name="pu[]" type="number" placeholder="PU" required class="border p-2 rounded w-full dark:bg-zinc-900"></div><div class='col-span-2'><button type="button" onclick="addItem()" class="bg-black text-white px-2 py-2 rounded w-full text-xs">+ Ligne</button></div></div></div>
        <button class="bg-black dark:bg-white dark:text-black text-white w-full py-4 rounded-full font-bold">Créer le devis</button>
    </form>
    <script>function addItem(){const d=document.createElement('div');d.className='grid grid-cols-12 gap-2 bg-gray-50 dark:bg-black p-2 rounded-xl mt-2';d.innerHTML=`<div class='col-span-6'><input name="service[]" placeholder="Service" required class="border p-2 rounded w-full dark:bg-zinc-900"></div><div class='col-span-2'><input name="qte[]" type="number" value="1" class="border p-2 rounded w-full dark:bg-zinc-900"></div><div class='col-span-2'><input name="pu[]" type="number" placeholder="PU" required class="border p-2 rounded w-full dark:bg-zinc-900"></div><div class='col-span-2'><button type="button" onclick="this.parentElement.parentElement.remove()" class="bg-red-500 text-white px-2 py-2 rounded w-full text-xs">X</button></div>`;document.getElementById('items').appendChild(d);}</script>
    """,user)

@app.route("/abonnement")
def abonnement():
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); cur=db.cursor()
    q="SELECT * FROM users WHERE id=%s" if USE_POSTGRES else "SELECT * FROM users WHERE id=?"
    cur.execute(q,(session['user_id'],)); user=cur.fetchone()
    return layout(f"""
    <h1 class='text-3xl font-black text-center'>Abonnement - Crypto Only</h1>
    <p class='text-center text-sm text-gray-500 mt-2'>Plus de MoMo - Uniquement USDT BEP20 / TRC20 + BNB + TRX</p>
    <div class='grid md:grid-cols-3 gap-4 mt-8 max-w-4xl mx-auto'>
        <div class='bg-white dark:bg-zinc-900 border p-6 rounded-[24px]'><h3 class='font-bold'>FREE</h3><p class='text-3xl font-bold my-2'>0</p><p class='text-sm'>5 devis</p></div>
        <div class='bg-black dark:bg-white dark:text-black text-white border-2 p-6 rounded-[24px]'><h3>STARTER</h3><p class='text-3xl font-bold my-2'>10 USDT</p>
            <div class='mt-4 space-y-2'>
                <a href='/pay/STARTER/USDT_BEP20' class='block bg-green-500 py-3 rounded-full text-center font-bold text-sm'>💵 USDT BEP20 - 10</a>
                <a href='/pay/STARTER/USDT_TRC20' class='block bg-blue-500 py-3 rounded-full text-center font-bold text-sm'>💵 USDT TRC20 - 10</a>
                <a href='/pay/STARTER/BNB' class='block bg-yellow-500 text-black py-3 rounded-full text-center font-bold text-sm'>🟡 BNB - 0.025</a>
                <a href='/pay/STARTER/TRX' class='block bg-red-500 py-3 rounded-full text-center font-bold text-sm'>🔴 TRX - 100</a>
            </div>
        </div>
        <div class='bg-white dark:bg-zinc-900 border p-6 rounded-[24px]'><h3>PRO</h3><p class='text-3xl font-bold my-2'>22 USDT</p>
            <div class='mt-4 space-y-2'>
                <a href='/pay/PRO/USDT_BEP20' class='block bg-green-600 text-white py-3 rounded-full text-center font-bold text-sm'>USDT BEP20 - 22</a>
                <a href='/pay/PRO/USDT_TRC20' class='block bg-blue-600 text-white py-3 rounded-full text-center font-bold text-sm'>USDT TRC20 - 22</a>
                <a href='/pay/PRO/BNB' class='block bg-yellow-600 text-white py-3 rounded-full text-center font-bold text-sm'>BNB - 0.055</a>
                <a href='/pay/PRO/TRX' class='block bg-red-600 text-white py-3 rounded-full text-center font-bold text-sm'>TRX - 220</a>
            </div>
        </div>
    </div>
    """,user)

@app.route("/pay/<plan>/<network>")
def pay(plan,network):
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); cur=db.cursor()
    q="SELECT * FROM users WHERE id=%s" if USE_POSTGRES else "SELECT * FROM users WHERE id=?"
    cur.execute(q,(session['user_id'],)); user=cur.fetchone()
    prices=ADMIN_CONFIG['prices'][plan]; amount=prices.get(network,0)
    if network in ["USDT_BEP20","BNB"]:
        info=f"<p class='font-mono text-xs break-all bg-gray-50 dark:bg-black p-3 rounded-xl border'>{ADMIN_CONFIG['crypto']['BSC_ADDRESS']}</p><p class='text-xs mt-2'>Réseau: BSC (BEP20) - Montant: {amount} {network}</p>"
    else:
        info=f"<p class='font-mono text-xs break-all bg-gray-50 dark:bg-black p-3 rounded-xl border'>{ADMIN_CONFIG['crypto']['TRON_ADDRESS']}</p><p class='text-xs mt-2'>Réseau: TRON (TRC20) - Montant: {amount} {network}</p>"
    return layout(f"""<div class='max-w-lg mx-auto bg-white dark:bg-zinc-900 p-6 rounded-[24px] border mt-6'><h2 class='text-xl font-bold'>Payer {plan} en {network} - Crypto Only</h2><div class='mt-4'>{info}</div><form method="POST" action="/verify_payment" class="mt-6 space-y-3"><input type="hidden" name="plan" value="{plan}"><input type="hidden" name="network" value="{network}"><input name="txid" placeholder="Colle TXID / Hash" required class="border p-3 rounded-xl w-full font-mono text-xs dark:bg-black"><button class="bg-black dark:bg-white dark:text-black text-white w-full py-3 rounded-full font-bold">Soumettre TXID</button></form></div>""",user)

@app.route("/verify_payment", methods=["POST"])
def verify_payment():
    if 'user_id' not in session: return redirect("/login")
    plan=request.form.get("plan"); network=request.form.get("network"); txid=request.form.get("txid","").strip()
    db=get_db(); cur=db.cursor()
    q="SELECT * FROM users WHERE id=%s" if USE_POSTGRES else "SELECT * FROM users WHERE id=?"
    cur.execute(q,(session['user_id'],)); user=cur.fetchone()
    ok,msg,status = verify_txid(network,txid)
    if not ok: return layout(f"<div class='bg-white dark:bg-zinc-900 p-6 rounded-[24px] border'><p class='text-red-600 font-bold'>{msg}</p><a href='/pay/{plan}/{network}' class='block bg-black text-white py-3 rounded-full text-center mt-4'>Corriger</a></div>",user)
    try:
        prices=ADMIN_CONFIG['prices'][plan]; amount=prices.get(network,0)
        qi="INSERT INTO payments (user_id,type,plan,method,network,amount,currency,txid,status,created_at,verified_data) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO payments (user_id,type,plan,method,network,amount,currency,txid,status,created_at,verified_data) VALUES (?,?,?,?,?,?,?,?,?,?,?)"
        cur.execute(qi,(session['user_id'],'subscription',plan,"CRYPTO",network,amount,network,txid,status,datetime.datetime.now().isoformat(),msg))
        db.commit()
        return layout(f"<div class='max-w-lg mx-auto bg-white dark:bg-zinc-900 p-8 rounded-[24px] border mt-10 text-center'><div class='text-5xl'>⏳</div><h2 class='text-2xl font-bold mt-4'>Paiement {network} en vérification</h2><p class='text-sm mt-2'>{msg}</p><p class='font-mono text-xs bg-gray-100 dark:bg-black p-2 rounded mt-3 break-all'>{txid}</p><a href='/dashboard' class='block bg-black text-white py-3 rounded-full mt-6'>Dashboard</a></div>",user)
    except Exception as e:
        return layout(f"<p>TXID déjà utilisé</p>",user)

# === ROUTE DEVIS CORRIGEE : OWNER vs CLIENT ===
@app.route("/devis/<int:did>", methods=["GET","POST"])
def view_devis(did):
    db=get_db(); cur=db.cursor()
    q="SELECT * FROM devis WHERE id=%s" if USE_POSTGRES else "SELECT * FROM devis WHERE id=?"
    cur.execute(q,(did,)); d=cur.fetchone()
    if not d: return layout("<p>Devis introuvable</p>")

    # Get seller info for payment addresses
    q_user="SELECT * FROM users WHERE id=%s" if USE_POSTGRES else "SELECT * FROM users WHERE id=?"
    user_id = d['user_id'] if isinstance(d, dict) else d[1]
    cur.execute(q_user,(user_id,)); seller=cur.fetchone()

    # Check if current visitor is owner
    is_owner = False
    if 'user_id' in session:
        if session['user_id'] == user_id:
            is_owner = True

    numero = d['numero'] if isinstance(d, dict) else d[2]
    client_name = d['client_name'] if isinstance(d, dict) else d[3]
    total = d['total'] if isinstance(d, dict) else d[5]
    acompte = d['acompte'] if isinstance(d, dict) else d[6]
    items_json = d['items_json'] if isinstance(d, dict) else d[7]
    views = d['views'] if isinstance(d, dict) else d[9]
    created_at = d['created_at'] if isinstance(d, dict) else d[10]

    # Increment views
    try:
        qv="UPDATE devis SET views=views+1 WHERE id=%s" if USE_POSTGRES else "UPDATE devis SET views=views+1 WHERE id=?"
        cur.execute(qv,(did,)); db.commit()
    except: pass

    items=json.loads(items_json or '[]')
    rows="".join([f"<tr><td class='p-3 border'>{i['service']}</td><td class='border p-3 text-center'>{fmt(i['qte'])}</td><td class='border p-3 text-right'>{fmt(i['pu'])} FCFA</td><td class='border p-3 text-right font-bold'>{fmt(i['total'])} FCFA</td></tr>" for i in items])

    base_url = request.host_url.rstrip('/')  # e.g. https://deviscloser-1.onrender.com
    devis_link = f"{base_url}/devis/{did}"
    wa_message = urllib.parse.quote(f"Bonjour {client_name}, voici votre devis {numero} : {fmt(total)} FCFA (Acompte {fmt(acompte)} FCFA à payer en crypto). Lien : {devis_link}")
    mail_subject = urllib.parse.quote(f"Devis {numero} - {fmt(total)} FCFA")
    mail_body = urllib.parse.quote(f"Bonjour {client_name},\n\nVoici votre devis {numero} :\nTotal: {fmt(total)} FCFA\nAcompte à payer (50%): {fmt(acompte)} FCFA en crypto (USDT BEP20/TRC20, BNB, TRX)\n\nLien pour accepter et payer : {devis_link}\n\nMerci !")

    # OWNER VIEW : show share buttons, no accept button
    if is_owner:
        cur.execute(q_user,(session['user_id'],)); user=cur.fetchone()
        return layout(f"""
        <div class='max-w-3xl mx-auto'>
            <div class='bg-green-50 dark:bg-green-900/20 border border-green-200 p-4 rounded-[24px] mb-6'>
                <b class='text-green-800 dark:text-green-300'>✅ Devis créé ! Maintenant envoie-le à ton client</b>
                <p class='text-xs mt-1'>Ton client verra le bouton "Accepter et payer". Toi tu vois les boutons d'envoi ci-dessous.</p>
            </div>

            <div class='bg-white dark:bg-zinc-900 p-8 rounded-[32px] border shadow-sm'>
                <div class='flex justify-between items-start'>
                    <div><h1 class='text-3xl font-black'>DEVIS {numero}</h1><p class='text-gray-500 mt-1'>Pour {client_name} - {views+1} vues - Créé le {created_at[:10] if created_at else ''}</p></div>
                    <span class='bg-gray-100 dark:bg-zinc-800 px-3 py-1 rounded-full text-xs'>Brouillon</span>
                </div>
                <table class='w-full mt-8 text-sm border rounded-xl overflow-hidden'><thead class='bg-gray-50 dark:bg-black'><tr><th class='p-3 text-left'>Service</th><th class='p-3'>Qté</th><th class='p-3 text-right'>PU</th><th class='p-3 text-right'>Total</th></tr></thead><tbody>{rows}</tbody></table>
                <div class='mt-6 bg-gray-50 dark:bg-black p-4 rounded-2xl flex justify-between items-center'>
                    <div><p class='text-sm text-gray-500'>Montant total</p><p class='text-2xl font-black'>{fmt(total)} FCFA</p></div>
                    <div class='text-right'><p class='text-sm text-gray-500'>Acompte à payer (50%)</p><p class='text-xl font-bold text-green-600'>{fmt(acompte)} FCFA en Crypto</p></div>
                </div>
            </div>

            <div class='mt-6 bg-white dark:bg-zinc-900 p-6 rounded-[32px] border'>
                <h2 class='text-xl font-bold'>📤 Envoyer au client</h2>
                <p class='text-sm text-gray-500 mt-1'>Le client recevra le lien avec le bouton "Accepter et payer en crypto"</p>
                <div class='grid md:grid-cols-3 gap-3 mt-4'>
                    <a href='https://wa.me/?text={wa_message}' target='_blank' class='bg-green-500 hover:bg-green-600 text-white p-4 rounded-2xl text-center font-bold'>💬 WhatsApp<br><span class='text-xs font-normal'>Envoyer sur WhatsApp</span></a>
                    <a href='mailto:?subject={mail_subject}&body={mail_body}' class='bg-blue-500 hover:bg-blue-600 text-white p-4 rounded-2xl text-center font-bold'>📧 Email<br><span class='text-xs font-normal'>Envoyer par mail</span></a>
                    <button onclick="navigator.clipboard.writeText('{devis_link}'); alert('Lien copié ! {devis_link}')" class='bg-black dark:bg-white dark:text-black text-white p-4 rounded-2xl text-center font-bold'>🔗 Copier lien<br><span class='text-xs font-normal'>Copier le lien</span></button>
                </div>
                <div class='mt-4 bg-gray-50 dark:bg-black p-3 rounded-xl'>
                    <p class='text-xs text-gray-500'>Lien du devis (à envoyer) :</p>
                    <p class='font-mono text-sm break-all mt-1'>{devis_link}</p>
                </div>
                <div class='mt-4 flex gap-2'>
                    <a href='/devis/{did}?preview=client' class='border px-4 py-2 rounded-full text-xs'>👁️ Voir comme client</a>
                    <a href='/dashboard' class='border px-4 py-2 rounded-full text-xs'>← Dashboard</a>
                </div>
            </div>
        </div>
        """,user)

    # CLIENT VIEW (public, no session or not owner) : show Accept and Pay
    else:
        # If POST from client clicking accept
        if request.method=="POST":
            return f"""
            <html><head>{BASE_HTML_HEAD}</head><body class='bg-green-50 dark:bg-black min-h-screen p-4'>
            <div class='max-w-lg mx-auto'>
                <div class='bg-white dark:bg-zinc-900 p-8 rounded-[32px] border mt-6'>
                    <h2 class='text-2xl font-black text-center'>Payer acompte {fmt(acompte)} FCFA</h2>
                    <p class='text-center text-sm text-gray-500 mt-2'>Devis {numero} pour {client_name} - 100% Crypto (Pas de MoMo)</p>
                    <p class='text-center text-xs mt-1'>Total: {fmt(total)} FCFA - Acompte 50% = {fmt(acompte)} FCFA</p>

                    <div class='mt-6 space-y-4'>
                        <div class='border-2 border-green-200 bg-green-50 dark:bg-green-900/20 p-4 rounded-2xl'>
                            <p class='font-bold text-sm'>💵 USDT BEP20 (BSC)</p>
                            <p class='font-mono text-[11px] break-all bg-white dark:bg-black p-2 rounded mt-2 border'>{ADMIN_CONFIG['crypto']['BSC_ADDRESS']}</p>
                            <p class='text-[11px] mt-2'>Montant: <b>{fmt(acompte)} FCFA ≈ équivalent en USDT à envoyer</b><br>Contacte le vendeur pour le montant exact en USDT</p>
                            <form method='POST' action='/verify_acompte/{did}' class='mt-3'>
                                <input type='hidden' name='network' value='USDT_BEP20'>
                                <input name='txid' placeholder='Colle TXID BEP20 0x... (66 chars)' required class='border p-3 rounded-xl w-full font-mono text-xs dark:bg-black'>
                                <button class='bg-green-600 text-white w-full py-3 rounded-full font-bold mt-2 text-sm'>✅ J'ai payé en USDT BEP20</button>
                            </form>
                        </div>

                        <div class='border-2 border-blue-200 bg-blue-50 dark:bg-blue-900/20 p-4 rounded-2xl'>
                            <p class='font-bold text-sm'>💵 USDT TRC20 (TRON)</p>
                            <p class='font-mono text-[11px] break-all bg-white dark:bg-black p-2 rounded mt-2 border'>{ADMIN_CONFIG['crypto']['TRON_ADDRESS']}</p>
                            <form method='POST' action='/verify_acompte/{did}' class='mt-3'>
                                <input type='hidden' name='network' value='USDT_TRC20'>
                                <input name='txid' placeholder='TXID TRC20 64 chars' required class='border p-3 rounded-xl w-full font-mono text-xs dark:bg-black'>
                                <button class='bg-blue-600 text-white w-full py-3 rounded-full font-bold mt-2 text-sm'>✅ J'ai payé en USDT TRC20</button>
                            </form>
                        </div>

                        <div class='grid grid-cols-2 gap-3'>
                            <div class='border p-3 rounded-2xl bg-yellow-50 dark:bg-yellow-900/20'>
                                <p class='font-bold text-xs'>🟡 BNB (BSC)</p>
                                <p class='font-mono text-[9px] break-all mt-1'>{ADMIN_CONFIG['crypto']['BSC_ADDRESS'][:20]}...</p>
                                <form method='POST' action='/verify_acompte/{did}' class='mt-2'>
                                    <input type='hidden' name='network' value='BNB'>
                                    <input name='txid' placeholder='0x...' required class='border p-2 rounded w-full font-mono text-[10px] dark:bg-black'>
                                    <button class='bg-yellow-500 text-black w-full py-2 rounded-full font-bold mt-1 text-xs'>Payé BNB</button>
                                </form>
                            </div>
                            <div class='border p-3 rounded-2xl bg-red-50 dark:bg-red-900/20'>
                                <p class='font-bold text-xs'>🔴 TRX (TRON)</p>
                                <p class='font-mono text-[9px] break-all mt-1'>{ADMIN_CONFIG['crypto']['TRON_ADDRESS'][:20]}...</p>
                                <form method='POST' action='/verify_acompte/{did}' class='mt-2'>
                                    <input type='hidden' name='network' value='TRX'>
                                    <input name='txid' placeholder='64 chars' required class='border p-2 rounded w-full font-mono text-[10px] dark:bg-black'>
                                    <button class='bg-red-500 text-white w-full py-2 rounded-full font-bold mt-1 text-xs'>Payé TRX</button>
                                </form>
                            </div>
                        </div>
                    </div>

                    <p class='text-[11px] text-gray-500 text-center mt-6'>100% Crypto - USDT BEP20/TRC20 + BNB + TRX - Pas de MoMo - Validation sous 2h</p>
                </div>
            </div>
            </div></body></html>
            """

        # CLIENT initial view
        is_preview = request.args.get("preview")=="client"
        preview_banner = "<div class='bg-yellow-100 border border-yellow-300 p-3 rounded-xl mb-4 text-center text-sm'><b>👁️ Aperçu vue client</b> - C'est ce que ton client voit <a href='/devis/{did}' class='underline'>Retour vue propriétaire</a></div>".replace("{did}",str(did)) if is_preview else ""
        return f"""
        <html><head>{BASE_HTML_HEAD}</head><body class='bg-gray-50 dark:bg-black min-h-screen p-4'>
        <div class='max-w-2xl mx-auto'>
            {preview_banner}
            <div class='bg-white dark:bg-zinc-900 p-8 rounded-[32px] border shadow-sm mt-4'>
                <h1 class='text-3xl font-black'>DEVIS {numero}</h1>
                <p class='text-gray-500 mt-1'>Pour {client_name} - {views+1} vues</p>
                <table class='w-full mt-6 text-sm border rounded-xl overflow-hidden'><thead class='bg-gray-50 dark:bg-black'><tr><th class='p-3 text-left'>Service</th><th class='p-3'>Qté</th><th class='p-3 text-right'>PU</th><th class='p-3 text-right'>Total</th></tr></thead><tbody>{rows}</tbody></table>
                <div class='mt-6 bg-gray-50 dark:bg-black p-4 rounded-2xl'>
                    <div class='flex justify-between'><span class='text-gray-500'>Montant total</span><b>{fmt(total)} FCFA</b></div>
                    <div class='flex justify-between mt-2'><span class='text-gray-500'>Acompte à payer (50%)</span><b class='text-green-600'>{fmt(acompte)} FCFA en Crypto</b></div>
                    <p class='text-[11px] text-gray-400 mt-2'>Paiement 100% crypto : USDT BEP20 / USDT TRC20 / BNB / TRX - Pas de MoMo</p>
                </div>
                <form method='POST' class='mt-6'>
                    <button class='bg-green-600 hover:bg-green-700 text-white w-full py-5 rounded-full font-black text-lg shadow-lg'>✅ Accepter et payer l'acompte</button>
                </form>
                <p class='text-xs text-center text-gray-400 mt-3'>Paiement sécurisé crypto - Validation manuelle sous 2h</p>
            </div>
        </div>
        </body></html>
        """

@app.route("/verify_acompte/<int:did>", methods=["POST"])
def verify_acompte(did):
    db=get_db(); cur=db.cursor()
    q="SELECT * FROM devis WHERE id=%s" if USE_POSTGRES else "SELECT * FROM devis WHERE id=?"
    cur.execute(q,(did,)); d=cur.fetchone()
    network=request.form.get("network"); txid=request.form.get("txid","").strip()
    ok,msg,status = verify_txid(network,txid)
    if not ok:
        return f"<html><head>{BASE_HTML_HEAD}</head><body class='bg-red-50 p-8 text-center'><p class='text-red-600 font-bold'>{msg}</p><a href='/devis/{did}' class='inline-block bg-black text-white px-6 py-3 rounded-full mt-4'>Retour</a></body></html>"
    try:
        user_id = d['user_id'] if isinstance(d, dict) else d[1]
        acompte = d['acompte'] if isinstance(d, dict) else d[6]
        qi="INSERT INTO payments (user_id,devis_id,type,method,network,amount,currency,txid,status,created_at,verified_data) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO payments (user_id,devis_id,type,method,network,amount,currency,txid,status,created_at,verified_data) VALUES (?,?,?,?,?,?,?,?,?,?,?)"
        cur.execute(qi,(user_id,did,'acompte',"CRYPTO",network,acompte,network,txid,status,datetime.datetime.now().isoformat(),msg))
        q_up="UPDATE devis SET status='Acompte en vérification crypto ⏳' WHERE id=%s" if USE_POSTGRES else "UPDATE devis SET status='Acompte en vérification crypto ⏳' WHERE id=?"
        cur.execute(q_up,(did,))
        db.commit()
    except Exception as e:
        if "UNIQUE" in str(e) or "duplicate" in str(e).lower():
            return f"<html><body><p>TXID déjà utilisé</p><a href='/devis/{did}'>Retour</a></body></html>"
        raise e
    return f"<html><head>{BASE_HTML_HEAD}</head><body class='bg-green-50 dark:bg-black flex items-center justify-center min-h-screen p-4'><div class='bg-white dark:bg-zinc-900 p-8 rounded-[32px] text-center border max-w-md'><div class='text-5xl'>⏳</div><h2 class='text-2xl font-bold mt-4'>Acompte crypto en vérification</h2><p class='text-sm mt-2'>{msg}</p><p class='font-mono text-xs bg-gray-100 dark:bg-black p-3 rounded mt-4 break-all'>{txid}</p><p class='text-xs mt-4'>Réseau: {network} - Validation sous 2h<br>Le vendeur sera notifié</p><a href='/devis/{did}' class='block bg-black dark:bg-white dark:text-black text-white py-3 rounded-full font-bold mt-6'>Retour au devis</a></div></body></html>"

@app.route("/settings", methods=["GET","POST"])
def settings():
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); cur=db.cursor()
    q="SELECT * FROM users WHERE id=%s" if USE_POSTGRES else "SELECT * FROM users WHERE id=?"
    cur.execute(q,(session['user_id'],)); user=cur.fetchone()
    if request.method=="POST":
        qi="UPDATE users SET usdt_bep20=%s, usdt_trc20=%s WHERE id=%s" if USE_POSTGRES else "UPDATE users SET usdt_bep20=?, usdt_trc20=? WHERE id=?"
        cur.execute(qi,(request.form.get("usdt_bep20"),request.form.get("usdt_trc20"),session['user_id']))
        db.commit(); return redirect("/dashboard")
    bep=user['usdt_bep20'] if isinstance(user,dict) else user[5]
    trc=user['usdt_trc20'] if isinstance(user,dict) else user[6]
    return layout(f"""
    <h1 class='text-2xl font-bold'>💳 Mes adresses crypto (pour recevoir acomptes)</h1>
    <p class='text-xs text-gray-500 mt-1'>100% crypto - Pas de MoMo - USDT BEP20/TRC20 + BNB + TRX</p>
    <form method="POST" class="mt-6 bg-white dark:bg-zinc-900 p-6 rounded-[24px] border space-y-4 max-w-xl">
        <div><label class='text-xs'>BSC Address (USDT BEP20 + BNB)</label><input name="usdt_bep20" value="{bep or ''}" placeholder="0x..." class="border p-3 rounded-xl w-full font-mono text-xs dark:bg-black mt-1"></div>
        <div><label class='text-xs'>TRON Address (USDT TRC20 + TRX)</label><input name="usdt_trc20" value="{trc or ''}" placeholder="T..." class="border p-3 rounded-xl w-full font-mono text-xs dark:bg-black mt-1"></div>
        <button class="bg-black dark:bg-white dark:text-black text-white w-full py-3 rounded-full font-bold">Enregistrer</button>
    </form>
    """,user)

@app.route("/admin")
def admin_panel():
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); cur=db.cursor()
    q="SELECT * FROM users WHERE id=%s" if USE_POSTGRES else "SELECT * FROM users WHERE id=?"
    cur.execute(q,(session['user_id'],)); user=cur.fetchone()
    is_admin=user['is_admin'] if isinstance(user,dict) else user[7]
    if not is_admin: return layout("<p>Accès refusé</p>",user)
    cur.execute("SELECT p.*, u.email FROM payments p JOIN users u ON p.user_id=u.id ORDER BY p.id DESC")
    pays=cur.fetchall()
    rows="".join([f"<div class='bg-white dark:bg-zinc-900 p-4 rounded-xl border flex justify-between'><div><b>{p['email'] if isinstance(p,dict) else p[12]}</b> - {p['plan'] if isinstance(p,dict) else p[4]} - {p['network'] if isinstance(p,dict) else p[6]} - <span class='font-mono text-xs'>{(p['txid'] if isinstance(p,dict) else p[8])[:20]}...</span><br><span class='text-xs'>{(p['status'] if isinstance(p,dict) else p[9])}</span></div><div><a href='/admin/approve/{p['id'] if isinstance(p,dict) else p[0]}' class='bg-green-600 text-white px-3 py-1 rounded-full text-xs'>✅</a></div></div>" for p in pays])
    return layout(f"<h1 class='text-2xl font-bold'>👑 Admin Crypto</h1><div class='mt-6 space-y-3'>{rows or 'Aucun paiement'}</div>",user)

@app.route("/admin/approve/<int:pid>")
def admin_approve(pid):
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); cur=db.cursor()
    q="SELECT * FROM users WHERE id=%s" if USE_POSTGRES else "SELECT * FROM users WHERE id=?"
    cur.execute(q,(session['user_id'],)); user=cur.fetchone()
    is_admin=user['is_admin'] if isinstance(user,dict) else user[7]
    if not is_admin: return "Non autorisé"
    q2="SELECT * FROM payments WHERE id=%s" if USE_POSTGRES else "SELECT * FROM payments WHERE id=?"
    cur.execute(q2,(pid,)); pay=cur.fetchone()
    exp=(datetime.datetime.now()+datetime.timedelta(days=30)).isoformat()
    plan=pay['plan'] if isinstance(pay,dict) else pay[4]
    uid=pay['user_id'] if isinstance(pay,dict) else pay[1]
    qu="UPDATE users SET plan=%s, expiration=%s WHERE id=%s" if USE_POSTGRES else "UPDATE users SET plan=?, expiration=? WHERE id=?"
    cur.execute(qu,(plan,exp,uid))
    qu2="UPDATE payments SET status='Approuvé ✅' WHERE id=%s" if USE_POSTGRES else "UPDATE payments SET status='Approuvé ✅' WHERE id=?"
    cur.execute(qu2,(pid,))
    db.commit()
    return redirect("/admin")

@app.route("/cgu")
def cgu(): return layout("<div class='bg-white dark:bg-zinc-900 p-8 rounded-[24px] border'><h1 class='text-2xl font-bold'>CGU - Crypto Only</h1><p class='mt-4 text-sm'>DevisCloser - 100% crypto - USDT BEP20/TRC20 + BNB + TRX - Pas de MoMo</p></div>")

@app.route("/confidentialite")
def confidentialite(): return layout("<div class='bg-white dark:bg-zinc-900 p-8 rounded-[24px] border'><h1>Confidentialité</h1><p class='text-sm mt-4'>Base Postgres persistante sécurisée</p></div>")

@app.route("/support")
def support(): return layout("<div class='bg-white dark:bg-zinc-900 p-8 rounded-[24px] border'><h1>Support</h1><p class='mt-4'>WhatsApp 2290156853149 - Crypto only - BscScan / TronScan</p></div>")

@app.route("/contact")
def contact(): return layout("<div class='bg-white dark:bg-zinc-900 p-8 rounded-[24px] border'><h1>Contact</h1><p>Sosthène - 2290156853149</p></div>")

@app.route("/logout")
def logout(): session.clear(); return redirect("/")

init_db()
if __name__=="__main__": app.run(host="0.0.0.0",port=8080)
