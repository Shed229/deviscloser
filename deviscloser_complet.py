
from flask import Flask, request, redirect, session, g
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, secrets, datetime, json, re

app = Flask(__name__)
app.secret_key = "deviscloser-v13-crypto-dark-2026"
VERSION="v13"

DB = "deviscloser.db"
ADMIN_CONFIG = {
    "momo_number": "2290156853149",
    "momo_name": "SOSTHENE HERVE EDOH",
    "whatsapp": "2290156853149",
    "crypto": {"BSC_ADDRESS": "0xeB3e09b4F53d863dEBb0d49591597741612b6FB1","TRON_ADDRESS": "THwRRQVtymKPwLdXdc7PmQvmvNaugX2cff"},
    "prices": {
        "STARTER": {"USDT_BEP20": 10, "USDT_TRC20": 10, "BNB": 0.025, "TRX": 100},
        "PRO": {"USDT_BEP20": 22, "USDT_TRC20": 22, "BNB": 0.055, "TRX": 220}
    }
}
ADMIN_EMAIL = "sosthene.herve@gmail.com"

def get_db():
    db=getattr(g,'_database',None)
    if db is None:
        db=g._database=sqlite3.connect(DB)
        db.row_factory=sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db=get_db()
        db.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT, plan TEXT DEFAULT 'FREE', expiration TEXT, momo_number TEXT, momo_name TEXT, usdt_bep20 TEXT, usdt_trc20 TEXT, bnb_address TEXT, trx_address TEXT, is_admin INTEGER DEFAULT 0)""")
        db.execute("""CREATE TABLE IF NOT EXISTS devis (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, numero TEXT, client_name TEXT, client_email TEXT, total REAL, acompte REAL, items_json TEXT, status TEXT DEFAULT 'Brouillon', views INTEGER DEFAULT 0, created_at TEXT)""")
        db.execute("""CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, devis_id INTEGER, type TEXT, plan TEXT, method TEXT, network TEXT, amount REAL, currency TEXT, txid TEXT UNIQUE, status TEXT, created_at TEXT, verified_data TEXT)""")
        db.commit()
        try:
            db.execute("UPDATE users SET is_admin=1 WHERE email LIKE '%sosthene%'")
            db.commit()
        except: pass

@app.teardown_appcontext
def close_connection(ex):
    db=getattr(g,'_database',None)
    if db: db.close()

BASE_HTML_HEAD = """
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.tailwindcss.com"></script>
<script>
tailwind.config = {darkMode: 'class'}
</script>
<style>
.dark body {background:#0a0a0a; color:#eee}
.dark .bg-white {background:#1a1a1a !important; border-color:#333 !important; color:#eee}
.dark .bg-gray-50 {background:#0a0a0a !important}
.dark .text-gray-500 {color:#888 !important}
.dark .border {border-color:#333 !important}
</style>
"""

def navbar(user=None):
    if not user:
        return f"""
        <nav class='bg-white dark:bg-black border-b p-3 flex justify-between items-center sticky top-0 z-50'>
            <b>DevisCloser</b>
            <div class='flex items-center gap-3'>
                <button onclick="toggleDark()" class='p-2 border rounded-full text-xs'>🌙/☀️</button>
                <a href='/login' class='text-sm'>Connexion</a>
            </div>
        </nav>
        """
    is_admin = user['is_admin'] if 'is_admin' in user.keys() else 0
    admin_link = "<a href='/admin' class='block px-4 py-3 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-xl'>👑 Admin Paiements</a>" if is_admin else ""
    return f"""
    <nav class='bg-white dark:bg-black border-b p-3 flex justify-between items-center sticky top-0 z-50'>
        <div class='flex items-center gap-3'><button id='menuBtn' class='p-2 border rounded-xl'>☰</button><b>DevisCloser</b></div>
        <div class='flex items-center gap-2'>
            <button onclick="toggleDark()" class='p-2 border rounded-full text-xs' title='Mode sombre/clair'>🌙</button>
            <span class='bg-black dark:bg-white dark:text-black text-white px-3 py-1 rounded-full text-xs'>{user['plan']}</span>
            <a href='/logout' class='text-red-500 text-xs'>Sortir</a>
        </div>
    </nav>
    <div id='sideMenu' class='fixed inset-0 z-40 hidden'>
        <div class='absolute inset-0 bg-black/40' onclick='toggleMenu()'></div>
        <div class='absolute left-0 top-0 h-full w-72 bg-white dark:bg-zinc-900 shadow-2xl p-4 overflow-y-auto'>
            <div class='flex justify-between items-center'><b>Menu</b><button onclick='toggleMenu()' class='p-2'>✕</button></div>
            <div class='mt-6 space-y-1'>
                <a href='/dashboard' class='block px-4 py-3 rounded-xl hover:bg-gray-100 dark:hover:bg-zinc-800'>📊 Dashboard</a>
                <a href='/create' class='block px-4 py-3 rounded-xl hover:bg-gray-100 dark:hover:bg-zinc-800'>➕ Nouveau devis</a>
                <a href='/abonnement' class='block px-4 py-3 rounded-xl hover:bg-gray-100 dark:hover:bg-zinc-800'>💎 Abonnement (Crypto only)</a>
                <a href='/settings' class='block px-4 py-3 rounded-xl hover:bg-gray-100 dark:hover:bg-zinc-800'>💳 Mes Paiements</a>
                <div class='border-t my-3'></div>
                <a href='/cgu' class='block px-4 py-3 rounded-xl hover:bg-gray-100 dark:hover:bg-zinc-800'>📄 CGU</a>
                <a href='/confidentialite' class='block px-4 py-3 rounded-xl hover:bg-gray-100 dark:hover:bg-zinc-800'>🔒 Confidentialité</a>
                <a href='/support' class='block px-4 py-3 rounded-xl hover:bg-gray-100 dark:hover:bg-zinc-800'>💬 Support</a>
                <a href='/contact' class='block px-4 py-3 rounded-xl hover:bg-gray-100 dark:hover:bg-zinc-800'>📧 Contact</a>
                {admin_link}
            </div>
            <div class='absolute bottom-4 left-4 right-4 text-xs text-gray-400'>
                <p>v13 Crypto Only + Dark Mode</p><p>Sosthène Hervé EDOH</p>
                <button onclick="toggleDark()" class='mt-2 border px-3 py-1 rounded-full'>🌙 Mode sombre / ☀️ Clair</button>
            </div>
        </div>
    </div>
    <script>
    function toggleMenu(){{document.getElementById('sideMenu').classList.toggle('hidden')}}
    document.getElementById('menuBtn').onclick=toggleMenu;
    function toggleDark(){{
        const html=document.documentElement;
        html.classList.toggle('dark');
        localStorage.setItem('theme', html.classList.contains('dark')?'dark':'light');
        document.getElementById('darkIcon').innerText = html.classList.contains('dark')?'☀️':'🌙';
    }}
    (function(){{
        if(localStorage.getItem('theme')==='dark'){{document.documentElement.classList.add('dark')}}
    }})();
    </script>
    """

def footer():
    return """
    <footer class='mt-16 border-t bg-white dark:bg-zinc-900 p-8 text-sm'>
        <div class='max-w-5xl mx-auto grid md:grid-cols-4 gap-6'>
            <div><b>DevisCloser</b><p class='text-gray-500 mt-2'>Le devis qui te fait payer.</p><p class='text-xs text-gray-400 mt-2'>© 2026</p></div>
            <div><b>Produit</b><div class='mt-2 space-y-1 text-gray-600 dark:text-gray-300'><a href='/abonnement' class='block'>Abonnement Crypto</a><a href='/cgu' class='block'>CGU</a></div></div>
            <div><b>Support</b><div class='mt-2 space-y-1'><a href='/support' class='block'>Support</a><a href='https://wa.me/2290156853149' class='block'>WhatsApp</a></div></div>
            <div><b>Crypto Only</b><p class='text-xs text-gray-500 mt-2'>USDT BEP20/TRC20 + BNB + TRX<br>Validation manuelle sous 2h<br><span id='darkIcon'>🌙</span> Mode sombre dispo</p></div>
        </div>
    </footer>
    """

def layout(content,user=None):
    nav=navbar(user)
    foot=footer()
    return f"<html class=''><head>{BASE_HTML_HEAD}<title>DevisCloser v13</title></head><body class='bg-gray-50 dark:bg-black transition-colors'>{nav}<div class='max-w-5xl mx-auto p-4'>{content}</div>{foot}</body></html>"

def verify_txid(method,network,txid):
    txid=txid.strip()
    db=get_db()
    if db.execute("SELECT * FROM payments WHERE txid=?",(txid,)).fetchone():
        return False,"❌ TXID déjà utilisé !","DUPLICATE"
    if network in ["USDT_BEP20","BNB"]:
        if not txid.startswith("0x") or len(txid)!=66: return False,"❌ TXID BEP20/BNB invalide: 0x + 66 chars","INVALID"
        if not re.match(r'^0x[a-fA-F0-9]{64}$', txid): return False,"❌ TXID hex invalide","INVALID"
        return True,"✅ TX valide - En attente vérification","PENDING"
    if network in ["USDT_TRC20","TRX"]:
        if len(txid)!=64: return False,"❌ TXID TRC20/TRX: 64 chars","INVALID"
        if not re.match(r'^[a-fA-F0-9]{64}$', txid): return False,"❌ TXID hex invalide","INVALID"
        return True,"✅ TX valide - En attente vérification","PENDING"
    if method=="MOMO":
        if len(txid)<6: return False,"ID MoMo trop court","INVALID"
        return True,"⏳ MoMo en vérification","PENDING"
    return False,"Réseau inconnu","INVALID"

@app.route("/")
def home():
    if 'user_id' in session: return redirect("/dashboard")
    return layout("""
    <div class='min-h-[80vh] flex flex-col justify-center max-w-4xl mx-auto text-center px-4'>
        <h1 class='text-6xl md:text-8xl font-black tracking-tight leading-[0.9]'>Le devis<br>qui te fait<br><span class='bg-black dark:bg-white dark:text-black text-white px-4 rounded-full'>payer.</span></h1>
        <p class='mt-8 text-2xl md:text-3xl font-medium'>Crée ton devis. Encaisse ton acompte. C'est tout.</p>
        <div class='mt-10 flex flex-col md:flex-row gap-4 justify-center'>
            <a href='/register' class='bg-black dark:bg-white dark:text-black text-white px-10 py-5 rounded-full font-bold text-lg'>S'inscrire - Gratuit</a>
            <a href='/login' class='border-2 border-black dark:border-white px-10 py-5 rounded-full font-bold text-lg'>Connexion</a>
        </div>
        <div class='mt-6 flex justify-center'><button onclick="toggleDark()" class='border px-6 py-2 rounded-full text-sm'>🌙 Essayer le mode sombre / clair</button></div>
        <div class='mt-12 grid md:grid-cols-3 gap-4 text-left'>
            <div class='bg-white dark:bg-zinc-900 p-6 rounded-[24px] border'><div class='text-3xl'>📄</div><b>Devis pro 30s</b><p class='text-sm text-gray-500 mt-2'>Multi-lignes, TVA, remise</p></div>
            <div class='bg-white dark:bg-zinc-900 p-6 rounded-[24px] border'><div class='text-3xl'>💎</div><b>100% Crypto</b><p class='text-sm text-gray-500 mt-2'>USDT BEP20/TRC20 + BNB + TRX - Pas de MoMo pour abonnement</p></div>
            <div class='bg-white dark:bg-zinc-900 p-6 rounded-[24px] border'><div class='text-3xl'>🌙</div><b>Mode sombre</b><p class='text-sm text-gray-500 mt-2'>Travail de nuit? Passe en sombre.</p></div>
        </div>
    </div>
    """)

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        email=request.form.get("email","").lower().strip(); pwd=request.form.get("password","")
        db=get_db()
        try:
            db.execute("INSERT INTO users (email,password,plan) VALUES (?,?,?)",(email,generate_password_hash(pwd),"FREE"))
            db.commit()
            user=db.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
            session['user_id']=user['id']; return redirect("/dashboard")
        except: return layout("<p>Email déjà utilisé</p>")
    return layout("<div class='max-w-sm mx-auto bg-white dark:bg-zinc-900 p-6 rounded-[24px] mt-16 border'><h2 class='text-xl font-bold'>Inscription</h2><form method='POST' class='mt-4 space-y-3'><input name='email' type='email' required class='border p-3 rounded-xl w-full dark:bg-black'><input name='password' type='password' required class='border p-3 rounded-xl w-full dark:bg-black'><button class='bg-black dark:bg-white dark:text-black text-white w-full py-3 rounded-full font-bold'>Créer</button></form></div>")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form.get("email","").lower().strip(); pwd=request.form.get("password","")
        db=get_db(); user=db.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
        if user and check_password_hash(user['password'],pwd):
            session['user_id']=user['id']; return redirect("/dashboard")
        return layout("<p>Faux</p>")
    return layout("<div class='max-w-sm mx-auto bg-white dark:bg-zinc-900 p-6 rounded-[24px] mt-16 border'><h2 class='text-xl font-bold'>Connexion</h2><form method='POST' class='mt-4 space-y-3'><input name='email' type='email' required class='border p-3 rounded-xl w-full dark:bg-black'><input name='password' type='password' required class='border p-3 rounded-xl w-full dark:bg-black'><button class='bg-black dark:bg-white dark:text-black text-white w-full py-3 rounded-full font-bold'>Entrer</button></form></div>")

@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    devis=db.execute("SELECT * FROM devis WHERE user_id=? ORDER BY id DESC",(user['id'],)).fetchall()
    pending=db.execute("SELECT * FROM payments WHERE user_id=? AND status LIKE '%PENDING%'",(user['id'],)).fetchall()
    rows=""
    for d in devis:
        rows+=f"<div class='bg-white dark:bg-zinc-900 p-4 rounded-2xl border flex justify-between'><div><b>{d['numero']}</b> - {d['client_name']} - {d['total']:.0f}F</div><a href='/devis/{d['id']}' class='bg-black dark:bg-white dark:text-black text-white px-3 py-1 rounded-full text-xs'>Voir</a></div>"
    if not rows:
        rows="<div class='bg-white dark:bg-zinc-900 border-2 border-dashed rounded-[32px] p-12 text-center'><div class='text-6xl'>✨</div><h3 class='text-2xl font-bold mt-4'>Aucun devis</h3><p class='text-gray-500'>Ta devise: Crée ton devis. Encaisse ton acompte.</p><a href='/create' class='inline-block bg-black dark:bg-white dark:text-black text-white px-8 py-4 rounded-full font-bold mt-6'>+ Nouveau</a></div>"
    pending_html=f"<div class='bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 p-4 rounded-2xl mb-6'><b>⏳ {len(pending)} paiement(s) en vérification</b><p class='text-xs'>Validation sous 2h - WhatsApp 2290156853149</p></div>" if pending else ""
    return layout(f"""
    <div class='flex justify-between items-center'><h1 class='text-3xl font-black'>Dashboard - {user['plan']}</h1><button onclick="toggleDark()" class='border px-4 py-2 rounded-full text-xs'>🌙/☀️</button></div>
    {pending_html}
    <div class='grid grid-cols-3 gap-3 mt-6'>
        <div class='bg-black text-white dark:bg-white dark:text-black p-5 rounded-[24px]'><p class='text-xs'>DEVIS</p><p class='text-3xl font-black'>{len(devis)}</p></div>
        <div class='bg-white dark:bg-zinc-900 border p-5 rounded-[24px]'><p class='text-xs'>VUES</p><p class='text-3xl font-black'>{sum(d['views'] or 0 for d in devis)}</p></div>
        <div class='bg-green-500 text-white p-5 rounded-[24px]'><p class='text-xs'>PAYÉS</p><p class='text-3xl font-black'>{len([d for d in devis if 'Payé' in (d['status'] or '')])}</p></div>
    </div>
    <div class='mt-8 space-y-3'>{rows}</div>
    <a href='/create' class='fixed bottom-6 left-1/2 -translate-x-1/2 bg-black dark:bg-white dark:text-black text-white px-8 py-4 rounded-full font-bold shadow-2xl md:hidden'>+ Nouveau</a>
    """,user)

@app.route("/settings", methods=["GET","POST"])
def settings():
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    if request.method=="POST":
        db.execute("UPDATE users SET momo_number=?, momo_name=?, usdt_bep20=?, usdt_trc20=? WHERE id=?",(request.form.get("momo_number"),request.form.get("momo_name"),request.form.get("usdt_bep20"),request.form.get("usdt_trc20"),user['id']))
        db.commit(); return redirect("/dashboard")
    return layout(f"""
    <h1 class='text-2xl font-bold'>💳 Mes paiements</h1>
    <p class='text-xs text-gray-500'>Pour recevoir les acomptes de tes clients (MoMo reste pour acomptes, crypto pour tout)</p>
    <form method="POST" class="mt-6 bg-white dark:bg-zinc-900 p-6 rounded-[24px] border space-y-4 max-w-xl">
        <input name="momo_number" value="{user['momo_number'] or ''}" placeholder="MoMo pour acomptes clients" class="border p-3 rounded-xl w-full dark:bg-black">
        <input name="usdt_bep20" value="{user['usdt_bep20'] or ''}" placeholder="BSC 0x... (USDT BEP20 + BNB)" class="border p-3 rounded-xl w-full font-mono text-xs dark:bg-black">
        <input name="usdt_trc20" value="{user['usdt_trc20'] or ''}" placeholder="TRON T... (USDT TRC20 + TRX)" class="border p-3 rounded-xl w-full font-mono text-xs dark:bg-black">
        <button class="bg-black dark:bg-white dark:text-black text-white w-full py-3 rounded-full font-bold">Enregistrer</button>
    </form>
    """,user)

@app.route("/create", methods=["GET","POST"])
def create():
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    if request.method=="POST":
        numero=f"DV-{secrets.token_hex(3).upper()}"
        services=request.form.getlist("service[]"); qtes=request.form.getlist("qte[]"); pus=request.form.getlist("pu[]")
        items=[]; subtotal=0
        for s,q,p in zip(services,qtes,pus):
            if not s: continue
            try: q=float(q); p=float(p)
            except: q=1; p=0
            mt=q*p; subtotal+=mt; items.append({"service":s,"qte":q,"pu":p,"total":mt})
        total=subtotal; acompte=total*0.5
        db.execute("INSERT INTO devis (user_id,numero,client_name,client_email,total,acompte,items_json,status,created_at,views) VALUES (?,?,?,?,?,?,?,?,?,?)",(user['id'],numero,request.form.get("client_name"),request.form.get("client_email"),total,acompte,json.dumps(items),"Brouillon",datetime.datetime.now().isoformat(),0))
        db.commit()
        d=db.execute("SELECT * FROM devis WHERE numero=?",(numero,)).fetchone()
        return redirect(f"/devis/{d['id']}")
    return layout("""
    <h1 class='text-2xl font-bold'>+ Nouveau devis</h1>
    <form method="POST" class="mt-6 bg-white dark:bg-zinc-900 p-6 rounded-[24px] border space-y-3 max-w-3xl">
        <div class='grid md:grid-cols-2 gap-3'><input name="client_name" placeholder="Nom client *" required class="border p-3 rounded-xl w-full dark:bg-black"><input name="client_email" placeholder="WhatsApp / Email" class="border p-3 rounded-xl w-full dark:bg-black"></div>
        <div id="items"><div class='grid grid-cols-12 gap-2 bg-gray-50 dark:bg-black p-2 rounded-xl'><div class='col-span-6'><input name="service[]" placeholder="Service" required class="border p-2 rounded w-full dark:bg-zinc-900"></div><div class='col-span-2'><input name="qte[]" type="number" value="1" class="border p-2 rounded w-full dark:bg-zinc-900"></div><div class='col-span-2'><input name="pu[]" type="number" placeholder="PU" required class="border p-2 rounded w-full dark:bg-zinc-900"></div><div class='col-span-2'><button type="button" onclick="addItem()" class="bg-black dark:bg-white dark:text-black text-white px-2 py-2 rounded w-full text-xs">+ Ligne</button></div></div></div>
        <button class="bg-black dark:bg-white dark:text-black text-white w-full py-4 rounded-full font-bold">Créer</button>
    </form>
    <script>function addItem(){const d=document.createElement('div');d.className='grid grid-cols-12 gap-2 bg-gray-50 dark:bg-black p-2 rounded-xl mt-2';d.innerHTML=`<div class='col-span-6'><input name="service[]" placeholder="Service" required class="border p-2 rounded w-full dark:bg-zinc-900"></div><div class='col-span-2'><input name="qte[]" type="number" value="1" class="border p-2 rounded w-full dark:bg-zinc-900"></div><div class='col-span-2'><input name="pu[]" type="number" placeholder="PU" required class="border p-2 rounded w-full dark:bg-zinc-900"></div><div class='col-span-2'><button type="button" onclick="this.parentElement.parentElement.remove()" class="bg-red-500 text-white px-2 py-2 rounded w-full text-xs">X</button></div>`;document.getElementById('items').appendChild(d);}</script>
    """,user)

@app.route("/abonnement")
def abonnement():
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    return layout(f"""
    <h1 class='text-3xl font-black text-center'>Abonnement - Crypto Only</h1>
    <p class='text-center text-sm text-gray-500 mt-2'>Plus de MoMo pour l'abonnement - 100% crypto sécurisé</p>
    <p class='text-center mt-2'><button onclick="toggleDark()" class='border px-4 py-1 rounded-full text-xs'>🌙 Mode sombre / ☀️ Clair</button></p>
    <div class='grid md:grid-cols-3 gap-4 mt-8 max-w-4xl mx-auto'>
        <div class='bg-white dark:bg-zinc-900 border p-6 rounded-[24px]'><h3 class='font-bold'>FREE</h3><p class='text-3xl font-bold my-2'>0F</p><p class='text-sm'>5 devis à vie</p></div>
        <div class='bg-black dark:bg-white dark:text-black text-white border-2 border-black dark:border-white p-6 rounded-[24px] relative'><span class='absolute -top-3 left-6 bg-green-500 text-white text-xs px-3 py-1 rounded-full'>Populaire</span><h3 class='font-bold'>STARTER</h3><p class='text-3xl font-bold my-2'>10$<span class='text-sm font-normal'>/mois</span></p><p class='text-sm opacity-80'>35 devis/mois</p>
            <div class='mt-4 space-y-2'>
                <a href='/pay/STARTER/USDT_BEP20' class='block bg-green-500 text-white py-3 rounded-full text-center font-bold text-sm'>💵 USDT BEP20 - 10$</a>
                <a href='/pay/STARTER/USDT_TRC20' class='block bg-blue-500 text-white py-3 rounded-full text-center font-bold text-sm'>💵 USDT TRC20 - 10$</a>
                <a href='/pay/STARTER/BNB' class='block bg-yellow-500 text-black py-3 rounded-full text-center font-bold text-sm'>🟡 BNB - 0.025</a>
                <a href='/pay/STARTER/TRX' class='block bg-red-500 text-white py-3 rounded-full text-center font-bold text-sm'>🔴 TRX - 100</a>
            </div>
        </div>
        <div class='bg-white dark:bg-zinc-900 border p-6 rounded-[24px]'><h3 class='font-bold'>PRO</h3><p class='text-3xl font-bold my-2'>22$<span class='text-sm font-normal'>/mois</span></p><p class='text-sm'>Illimité</p>
            <div class='mt-4 space-y-2'>
                <a href='/pay/PRO/USDT_BEP20' class='block bg-green-600 text-white py-3 rounded-full text-center font-bold text-sm'>💵 USDT BEP20 - 22$</a>
                <a href='/pay/PRO/USDT_TRC20' class='block bg-blue-600 text-white py-3 rounded-full text-center font-bold text-sm'>💵 USDT TRC20 - 22$</a>
                <a href='/pay/PRO/BNB' class='block bg-yellow-600 text-white py-3 rounded-full text-center font-bold text-sm'>🟡 BNB - 0.055</a>
                <a href='/pay/PRO/TRX' class='block bg-red-600 text-white py-3 rounded-full text-center font-bold text-sm'>🔴 TRX - 220</a>
            </div>
        </div>
    </div>
    <div class='mt-8 bg-green-50 dark:bg-green-900/20 border border-green-200 p-4 rounded-2xl max-w-4xl mx-auto text-center'><b class='text-sm'>✅ 100% Crypto - Sécurisé - Pas de MoMo pour abonnement</b><p class='text-xs mt-1'>USDT BEP20/TRC20 + BNB + TRX - Adresses: BSC {ADMIN_CONFIG['crypto']['BSC_ADDRESS'][:10]}... / TRON {ADMIN_CONFIG['crypto']['TRON_ADDRESS'][:10]}...<br>MoMo reste disponible pour les acomptes de tes clients</p></div>
    """,user)

@app.route("/pricing")
def pricing(): return redirect("/abonnement")

@app.route("/pay/<plan>/<network>")
def pay(plan,network):
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    if network=="MOMO":
        return layout("<div class='max-w-lg mx-auto bg-white dark:bg-zinc-900 p-6 rounded-[24px] border mt-10 text-center'><p class='text-red-600 font-bold'>❌ MoMo supprimé pour abonnement</p><p class='text-sm mt-2'>Abonnement 100% crypto only: USDT BEP20/TRC20 + BNB + TRX</p><a href='/abonnement' class='block bg-black dark:bg-white dark:text-black text-white py-3 rounded-full font-bold mt-4'>Voir abonnements crypto</a></div>",user)
    prices=ADMIN_CONFIG['prices'][plan]
    amount=prices.get(network,0)
    if network in ["USDT_BEP20","BNB"]:
        info=f"<p class='font-mono text-xs break-all bg-gray-50 dark:bg-black p-3 rounded-xl border'>{ADMIN_CONFIG['crypto']['BSC_ADDRESS']}</p><div class='bg-green-50 dark:bg-green-900/20 p-3 rounded-xl mt-3 text-sm'><b>Réseau BSC - {amount} {network}</b><br>Copie hash TX 0x... 66 chars sur BscScan</div>"
    else:
        info=f"<p class='font-mono text-xs break-all bg-gray-50 dark:bg-black p-3 rounded-xl border'>{ADMIN_CONFIG['crypto']['TRON_ADDRESS']}</p><div class='bg-blue-50 dark:bg-blue-900/20 p-3 rounded-xl mt-3 text-sm'><b>Réseau TRON - {amount} {network}</b><br>Copie TXID 64 chars sur TronScan</div>"
    return layout(f"""<div class='max-w-lg mx-auto bg-white dark:bg-zinc-900 p-6 rounded-[24px] border mt-6'><h2 class='text-xl font-bold'>Payer {plan} via {network} - Crypto Only</h2><div class='mt-4'>{info}</div><form method="POST" action="/verify_payment" class="mt-6 space-y-3"><input type="hidden" name="plan" value="{plan}"><input type="hidden" name="network" value="{network}"><input type="hidden" name="method" value="CRYPTO"><input name="txid" placeholder="TXID / Hash" required class="border p-3 rounded-xl w-full font-mono text-xs dark:bg-black"><button class="bg-black dark:bg-white dark:text-black text-white w-full py-3 rounded-full font-bold">Soumettre pour vérification</button></form></div>""",user)

@app.route("/verify_payment", methods=["POST"])
def verify_payment():
    if 'user_id' not in session: return redirect("/login")
    plan=request.form.get("plan"); network=request.form.get("network"); txid=request.form.get("txid","").strip()
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    ok,msg,status = verify_txid("CRYPTO",network,txid)
    if not ok: return layout(f"<div class='bg-white dark:bg-zinc-900 p-6 rounded-[24px] border'><p class='text-red-600 font-bold'>{msg}</p><a href='/pay/{plan}/{network}' class='block bg-black text-white py-3 rounded-full text-center mt-4'>Corriger</a></div>",user)
    try:
        prices=ADMIN_CONFIG['prices'][plan]; amount=prices.get(network,0)
        db.execute("INSERT INTO payments (user_id,type,plan,method,network,amount,currency,txid,status,created_at,verified_data) VALUES (?,?,?,?,?,?,?,?,?,?,?)",(user['id'],'subscription',plan,"CRYPTO",network,amount,network,txid,status,datetime.datetime.now().isoformat(),msg))
        db.commit()
        return layout(f"<div class='max-w-lg mx-auto bg-white dark:bg-zinc-900 p-8 rounded-[24px] border mt-10 text-center'><div class='text-5xl'>⏳</div><h2 class='text-2xl font-bold mt-4'>Paiement {network} en vérification</h2><p class='text-sm mt-2'>{msg}</p><p class='font-mono text-xs bg-gray-100 dark:bg-black p-2 rounded mt-3 break-all'>{txid}</p><div class='bg-yellow-50 dark:bg-yellow-900/20 border p-4 rounded-xl mt-6 text-left text-xs'><b>Validation manuelle sous 2h</b><br>WhatsApp 2290156853149 avec preuve</div><a href='/dashboard' class='block bg-black dark:bg-white dark:text-black text-white py-3 rounded-full font-bold mt-6'>Dashboard</a></div>",user)
    except Exception as e:
        if "UNIQUE" in str(e): return layout("<p>TXID déjà utilisé</p>",user)
        raise e

@app.route("/admin")
def admin_panel():
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    if not user['is_admin']: return layout("<p>Accès refusé</p>",user)
    pays=db.execute("SELECT p.*, u.email FROM payments p JOIN users u ON p.user_id=u.id ORDER BY p.id DESC").fetchall()
    rows="".join([f"<div class='bg-white dark:bg-zinc-900 p-4 rounded-xl border flex justify-between'><div><b>{p['email']}</b> - {p['plan']} - {p['network']} - <span class='font-mono text-xs'>{p['txid'][:20]}...</span><br><span class='text-xs'>{p['status']}</span></div><div><a href='/admin/approve/{p['id']}' class='bg-green-600 text-white px-3 py-1 rounded-full text-xs'>✅ Approuver</a> <a href='/admin/reject/{p['id']}' class='bg-red-500 text-white px-3 py-1 rounded-full text-xs'>❌</a></div></div>" for p in pays])
    return layout(f"<h1 class='text-2xl font-bold'>👑 Admin Crypto Payments</h1><p class='text-xs'>Vérifie TXID sur BscScan.com (BEP20/BNB) et TronScan.org (TRC20/TRX)</p><div class='mt-6 space-y-3'>{rows or 'Aucun'}</div>",user)

@app.route("/admin/approve/<int:pid>")
def admin_approve(pid):
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    if not user['is_admin']: return "Non autorisé"
    pay=db.execute("SELECT * FROM payments WHERE id=?",(pid,)).fetchone()
    exp=(datetime.datetime.now()+datetime.timedelta(days=30)).isoformat()
    db.execute("UPDATE users SET plan=?, expiration=? WHERE id=?",(pay['plan'],exp,pay['user_id']))
    db.execute("UPDATE payments SET status='Approuvé ✅' WHERE id=?",(pid,))
    db.commit()
    return redirect("/admin")

@app.route("/admin/reject/<int:pid>")
def admin_reject(pid):
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    if not user['is_admin']: return "Non autorisé"
    db.execute("UPDATE payments SET status='Rejeté ❌' WHERE id=?",(pid,))
    db.commit()
    return redirect("/admin")

@app.route("/devis/<int:did>", methods=["GET","POST"])
def view_devis(did):
    db=get_db(); d=db.execute("SELECT * FROM devis WHERE id=?",(did,)).fetchone()
    if not d: return "Introuvable"
    seller=db.execute("SELECT * FROM users WHERE id=?",(d['user_id'],)).fetchone()
    if request.method=="POST":
        return f"<html><head>{BASE_HTML_HEAD}</head><body class='bg-green-50 dark:bg-black p-4'><div class='max-w-4xl mx-auto bg-white dark:bg-zinc-900 p-6 rounded-[24px] border'><h2 class='text-center font-bold'>Payer acompte {d['acompte']}F - Crypto + MoMo pour clients</h2><div class='grid md:grid-cols-2 gap-4 mt-6'><div class='border p-4 rounded-2xl'><p>📱 MoMo (pour clients Bénin)</p><form method='POST' action='/verify_acompte/{did}'><input type='hidden' name='network' value='MOMO'><input name='txid' placeholder='ID MoMo' required class='border p-2 rounded w-full text-xs dark:bg-black'><button class='bg-black dark:bg-white dark:text-black text-white w-full py-2 rounded-full mt-2 text-xs'>J'ai payé MoMo</button></form></div><div class='border p-4 rounded-2xl'><p>💵 USDT/BNB/TRX</p><form method='POST' action='/verify_acompte/{did}'><input type='hidden' name='network' value='USDT_BEP20'><input name='txid' placeholder='0x...' required class='border p-2 rounded w-full text-xs dark:bg-black'><button class='bg-green-600 text-white w-full py-2 rounded-full mt-2 text-xs'>J'ai payé Crypto</button></form></div></div></div></body></html>"
    db.execute("UPDATE devis SET views=views+1 WHERE id=?",(did,)); db.commit()
    items=json.loads(d['items_json'] or '[]'); rows="".join([f"<tr><td class='p-2 border'>{i['service']}</td><td class='border p-2'>{i['qte']}</td><td class='border p-2'>{i['pu']}</td><td class='border p-2'>{i['total']}</td></tr>" for i in items])
    return f"<html><head>{BASE_HTML_HEAD}</head><body class='bg-gray-50 dark:bg-black p-4'><div class='max-w-2xl mx-auto bg-white dark:bg-zinc-900 p-8 rounded-[24px] border'><h1 class='text-2xl font-bold'>DEVIS {d['numero']}</h1><p>{d['client_name']} - {d['views']} vues</p><table class='w-full mt-4 text-sm border'><tr><th class='border p-2'>Service</th><th>Qté</th><th>PU</th><th>Total</th></tr>{rows}</table><p class='mt-4 font-bold'>Total {d['total']}F - Acompte {d['acompte']}F</p><form method='POST' class='mt-6'><button class='bg-green-600 text-white w-full py-4 rounded-full font-bold'>✅ Accepter et payer</button></form></div></body></html>"

@app.route("/verify_acompte/<int:did>", methods=["POST"])
def verify_acompte(did):
    db=get_db(); d=db.execute("SELECT * FROM devis WHERE id=?",(did,)).fetchone()
    network=request.form.get("network"); txid=request.form.get("txid","").strip()
    method="MOMO" if network=="MOMO" else "CRYPTO"
    ok,msg,status = verify_txid(method,network,txid)
    if not ok: return f"<p>{msg}</p><a href='/devis/{did}'>Retour</a>"
    try:
        db.execute("INSERT INTO payments (user_id,devis_id,type,method,network,amount,currency,txid,status,created_at,verified_data) VALUES (?,?,?,?,?,?,?,?,?,?,?)",(d['user_id'],did,'acompte',method,network,d['acompte'],network,txid,status,datetime.datetime.now().isoformat(),msg))
        db.execute("UPDATE devis SET status='Acompte en vérification ⏳' WHERE id=?",(did,))
        db.commit()
    except: return "TXID déjà utilisé"
    return f"<html><head>{BASE_HTML_HEAD}</head><body class='bg-yellow-50 dark:bg-black flex items-center justify-center min-h-screen p-4'><div class='bg-white dark:bg-zinc-900 p-8 rounded-[24px] text-center border'><div class='text-5xl'>⏳</div><h2 class='text-xl font-bold mt-3'>Acompte en vérification</h2><p class='font-mono text-xs bg-gray-100 dark:bg-black p-2 rounded mt-3 break-all'>{txid}</p></div></body></html>"

@app.route("/cgu")
def cgu(): return layout("<div class='bg-white dark:bg-zinc-900 p-8 rounded-[24px] border'><h1 class='text-3xl font-bold'>CGU - Crypto Only</h1><p class='mt-4 text-sm'>Abonnement 100% crypto: USDT BEP20/TRC20 + BNB + TRX. MoMo supprimé pour abonnement, mais reste pour acomptes clients. Validation manuelle sous 2h.</p></div>")

@app.route("/confidentialite")
def confidentialite(): return layout("<div class='bg-white dark:bg-zinc-900 p-8 rounded-[24px] border'><h1 class='text-3xl font-bold'>Confidentialité + Dark Mode</h1><p class='text-sm mt-4'>Mode sombre disponible via bouton 🌙/☀️. Données stockées localement.</p></div>")

@app.route("/support")
def support(): return layout("<div class='bg-white dark:bg-zinc-900 p-8 rounded-[24px] border'><h1 class='text-3xl font-bold'>Support - Crypto Only</h1><p class='mt-4 text-sm'>WhatsApp 2290156853149 - Vérifie tes TXID sur BscScan.com et TronScan.org<br><button onclick='toggleDark()' class='border px-4 py-2 rounded-full mt-4'>🌙 Mode sombre / ☀️ Clair</button></p></div>")

@app.route("/contact")
def contact(): return layout("<div class='bg-white dark:bg-zinc-900 p-8 rounded-[24px] border'><h1 class='text-3xl font-bold'>Contact</h1><p class='mt-4'>Sosthène Hervé EDOH<br>2290156853149<br>BSC 0xeB3e09b4F53d863dEBb0d49591597741612b6FB1<br>TRON THwRRQVtymKPwLdXdc7PmQvmvNaugX2cff</p></div>")

@app.route("/logout")
def logout(): session.clear(); return redirect("/")

init_db()
if __name__=="__main__": app.run(host="0.0.0.0",port=8080)
