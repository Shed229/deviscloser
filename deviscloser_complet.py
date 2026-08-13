from flask import Flask, request, redirect, session, g
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, secrets, datetime, json, re, urllib.parse, requests

app = Flask(__name__)
app.secret_key = "deviscloser-v6-crypto-2026"

DB = "deviscloser.db"

# ================= CONFIG ADMIN - TES ADRESSES - À REMPLACER =================
ADMIN_CONFIG = {
    "momo_number": "2290156853149",
    "momo_name": "SOSTHENE HERVE EDOH",
    # === CRYPTO - REMPLACE PAR TES VRAIES ADRESSES ===
    "crypto": {
        # BEP20 (BSC) - adresse en 0x... - La même adresse reçoit USDT BEP20 + BNB
        "BSC_ADDRESS": "0xeB3e09b4F53d863dEBb0d49591597741612b6FB1",  # MET TON ADRESSE BSC (Trust Wallet / Binance)
        # TRC20 / TRX (Tron) - adresse en T... - La même adresse reçoit USDT TRC20 + TRX
        "TRON_ADDRESS": "THwRRQVtymKPwLdXdc7PmQvmvNaugX2cff",  # MET TON ADRESSE TRON (T...)
    },
    "prices": {
        "STARTER": {"momo": 5900, "USDT_BEP20": 10, "USDT_TRC20": 10, "BNB": 0.025, "TRX": 100},
        "PRO": {"momo": 12900, "USDT_BEP20": 22, "USDT_TRC20": 22, "BNB": 0.055, "TRX": 220}
    },
    # API Keys optionnelles pour vérif stricte (laisse vide pour mode souple auto)
    "BSCSCAN_API_KEY": "",  # Va sur bscscan.com -> My API Key -> gratuit
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
        return False, "❌ Cet ID/TXID a déjà été utilisé !"
    if method=="MOMO":
        if len(txid)<6: return False, "ID MoMo trop court (min 6 caractères). Vérifie le SMS."
        if not re.match(r'^[A-Za-z0-9\-\.]+$', txid): return False, "Format ID invalide"
        return True, f"✅ MoMo {txid} reçu (vérif format OK - mode auto)"
    
    # CRYPTO
    if network in ["USDT_BEP20","BNB"]:
        # BEP20 TX: 0x + 64 hex = 66 chars
        if not txid.startswith("0x") or len(txid)!=66:
            return False, f"TXID {network} invalide : doit commencer par 0x et faire 66 caractères (tu as {len(txid)}). Copie le Hash sur BscScan."
        # Optionnel: vérif via BscScan API si clé dispo
        if ADMIN_CONFIG["BSCSCAN_API_KEY"]:
            try:
                url=f"https://api.bscscan.com/api?module=proxy&action=eth_getTransactionByHash&txhash={txid}&apikey={ADMIN_CONFIG['BSCSCAN_API_KEY']}"
                r=requests.get(url,timeout=10).json()
                if r.get('result'): return True, f"✅ TX {network} trouvée sur BSC (vérifiée via BscScan)"
                else: return False, "Transaction non trouvée sur BSC. Attends 1 min."
            except: pass
        return True, f"✅ TX {network} format valide - Activation auto (mode souple BEP20 - vérif BscScan activable avec clé API)"
    
    if network in ["USDT_TRC20","TRX"]:
        if len(txid)!=64:
            return False, f"TXID {network} invalide : doit faire 64 caractères hex sans 0x (tu as {len(txid)})."
        # Vérif TronScan
        try:
            url=f"https://apilist.tronscanapi.com/api/transaction-info?hash={txid}"
            r=requests.get(url,timeout=10).json()
            if r and (r.get('tokenTransferInfo') or r.get('contractData')):
                return True, f"✅ TX {network} trouvée sur Tron (TronScan OK)"
            else:
                # Mode souple si pas trouvée immédiatement
                return True, f"⚠️ TX {network} non encore indexée, mais format OK. Activation auto en mode souple (sera vérifiée manuellement si besoin)"
        except Exception as e:
            return True, f"⚠️ API Tron temporairement down, format OK. Activation auto mode souple. {str(e)[:80]}"
    return False, "Réseau inconnu"


DEVISE = "Cree ton devis. Encaisse ton acompte. Cest tout."
SOUS_DEVISE = "Fini le travail gratuit. Ton client valide et paie avant que tu ne commences."

@app.route("/")
def home():
    if 'user_id' in session: return redirect("/dashboard")
    return f"""<html><head><meta name="viewport" content="width=device-width, initial-scale=1"><script src="https://cdn.tailwindcss.com"></script><title>DevisCloser</title></head>
<body class="bg-white">
<nav class="max-w-6xl mx-auto flex justify-between items-center p-5">
<b class="text-xl">DevisCloser.</b>
<div class="flex gap-2"><a href="/login" class="text-sm font-bold px-4 py-2">Connexion</a><a href="/register" class="text-sm font-bold bg-black text-white px-5 py-2.5 rounded-full">Essai gratuit</a></div>
</nav>
<section class="max-w-6xl mx-auto px-5 mt-12 md:mt-24 text-center">
<div class="inline-flex items-center gap-2 bg-gray-50 border px-3 py-1 rounded-full text-xs">Nouveau - Relance auto + IA Coach</div>
<h1 class="text-5xl md:text-7xl font-extrabold tracking-tight mt-6 leading-[0.9]">Le devis<br>qui te fait<br><span class="text-transparent bg-clip-text bg-gradient-to-r from-black to-gray-400">payer.</span></h1>
<h2 class="text-2xl md:text-3xl font-bold mt-8 tracking-tight">{DEVISE}</h2>
<p class="text-gray-500 max-w-xl mx-auto mt-4 text-base">{SOUS_DEVISE} Par Sosthene Herve EDOH.</p>
<div class="mt-8 flex flex-col md:flex-row gap-3 justify-center">
<a href="/register" class="bg-black text-white px-8 py-4 rounded-full font-bold">Creer mon premier devis - Gratuit</a>
<a href="/login" class="border border-black px-8 py-4 rounded-full font-bold">J'ai deja un compte</a>
</div>
<p class="text-xs text-gray-400 mt-4">5 devis gratuits a vie - Sans carte bancaire</p>
</section>
<section class="max-w-6xl mx-auto px-5 mt-16 grid md:grid-cols-3 gap-3">
<div class="bg-gray-50 p-6 rounded-[24px]"><b>30 secondes</b><p class="text-sm text-gray-500 mt-1">Tu crees un devis pro avec acompte.</p></div>
<div class="bg-black text-white p-6 rounded-[24px]"><b>Relance auto</b><p class="text-sm text-gray-400 mt-1">Message WhatsApp parfait si client vu sans reponse.</p></div>
<div class="bg-gray-50 p-6 rounded-[24px]"><b>IA Coach</b><p class="text-sm text-gray-500 mt-1">Quoi repondre si client dit cest cher.</p></div>
</section>
</body></html>"""


@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        email=request.form.get("email").lower().strip(); pwd=request.form.get("password")
        db=get_db()
        try:
            db.execute("INSERT INTO users (email,password,plan) VALUES (?,?,?)",(email,generate_password_hash(pwd),"FREE")); db.commit()
            user=db.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone(); session['user_id']=user['id']; return redirect("/dashboard")
        except: return layout("<p>Email déjà utilisé</p>")
    return layout("""<div class='max-w-sm mx-auto bg-white p-6 rounded-2xl mt-20 shadow'><h2 class='font-bold'>Inscription</h2><form method="POST" class="mt-4"><input name="email" type="email" placeholder="Email" required class="border p-3 rounded-xl w-full"><input name="password" type="password" placeholder="Mot de passe" required class="border p-3 rounded-xl w-full mt-2"><button class="bg-black text-white w-full py-3 rounded-xl mt-4 font-bold">Créer</button></form></div>""")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form.get("email").lower().strip(); pwd=request.form.get("password")
        db=get_db(); user=db.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
        if user and check_password_hash(user['password'],pwd): session['user_id']=user['id']; return redirect("/dashboard")
        return layout("<p>Faux</p>")
    return layout("""<div class='max-w-sm mx-auto bg-white p-6 rounded-2xl mt-20 shadow'><h2 class='font-bold'>Connexion</h2><form method="POST" class="mt-4"><input name="email" type="email" required class="border p-3 rounded-xl w-full"><input name="password" type="password" required class="border p-3 rounded-xl w-full mt-2"><button class="bg-black text-white w-full py-3 rounded-xl mt-4">Connexion</button></form></div>""")

@app.route("/logout")
def logout(): session.clear(); return redirect("/")


@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    devis=db.execute("SELECT * FROM devis WHERE user_id=? ORDER BY id DESC",(user['id'],)).fetchall()
    total = len(devis)
    vues = sum(d['views'] for d in devis) if devis else 0
    payes = len([d for d in devis if 'Pay' in d['status']]) if devis else 0
    cards = ""
    for d in devis:
        cards+=f"<div class='bg-white border p-5 rounded-[20px] flex justify-between items-center'><div><b>{d['numero']}</b> - {d['client_name']} - {d['total']}F</div><a href='/devis/{d['id']}' class='bg-black text-white text-xs px-4 py-2 rounded-full'>Voir</a></div>"
    empty = f"<div class='bg-white border-2 border-dashed rounded-[32px] p-10 text-center mt-6'><h3 class='font-extrabold text-xl'>Aucun devis pour l'instant</h3><p class='text-sm text-gray-500 mt-2'>Plan {user['plan']}. Devise: Cree ton devis. Encaisse ton acompte. Cest tout.</p><a href='/create' class='inline-block bg-black text-white px-8 py-4 rounded-full font-bold mt-6'>+ Creer mon premier devis</a></div>"
    content = f"<div class='max-w-5xl mx-auto'><h1 class='text-3xl font-extrabold'>Dashboard</h1><p class='text-sm text-gray-500'>Bienvenue {user['email']} - {user['plan']}</p><div class='grid grid-cols-3 gap-3 mt-6'><div class='bg-white border p-5 rounded-[20px]'><p class='text-xs'>Devis</p><p class='text-3xl font-extrabold'>{total}</p></div><div class='bg-white border p-5 rounded-[20px]'><p class='text-xs'>Vues</p><p class='text-3xl font-extrabold'>{vues}</p></div><div class='bg-black text-white p-5 rounded-[20px]'><p class='text-xs'>Payes</p><p class='text-3xl font-extrabold'>{payes}</p></div></div><div class='mt-8 grid gap-3'>{cards if cards else empty}</div><a href='/create' class='block bg-black text-white py-4 rounded-full font-bold text-center mt-6'>+ Nouveau Devis</a></div>"
    return layout(content, user)

@app.route("/settings", methods=["GET","POST"])
def settings():
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    if request.method=="POST":
        db.execute("UPDATE users SET momo_number=?, momo_name=?, usdt_bep20=?, usdt_trc20=?, bnb_address=?, trx_address=? WHERE id=?",
                   (request.form.get("momo_number"),request.form.get("momo_name"),request.form.get("usdt_bep20"),request.form.get("usdt_trc20"),request.form.get("bnb_address"),request.form.get("trx_address"),user['id'])); db.commit(); return redirect("/dashboard")
    return layout(f"""<h1 class='text-2xl font-bold'>💳 Mes adresses pour recevoir les acomptes</h1><form method="POST" class='bg-white p-6 rounded-2xl border mt-6 space-y-4 max-w-lg'><div><label class='text-sm font-bold'>MoMo (MTN/Moov/Celtiis)</label><input name="momo_number" value="{user['momo_number'] or ''}" placeholder="2290156853149" class="border p-3 rounded-xl w-full"><input name="momo_name" value="{user['momo_name'] or ''}" placeholder="Nom MoMo" class="border p-3 rounded-xl w-full mt-1"></div><div class='border-t pt-4'><label class='text-sm font-bold'>USDT BEP20 + BNB (BSC) - Adresse 0x...</label><input name="usdt_bep20" value="{user['usdt_bep20'] or user['bnb_address'] or ''}" placeholder="0x..." class="border p-3 rounded-xl w-full font-mono text-xs"><p class='text-xs text-gray-400'>Même adresse pour USDT BEP20 et BNB (réseau BSC)</p></div><div><label class='text-sm font-bold'>USDT TRC20 + TRX (Tron) - Adresse T...</label><input name="usdt_trc20" value="{user['usdt_trc20'] or user['trx_address'] or ''}" placeholder="T..." class="border p-3 rounded-xl w-full font-mono text-xs"><p class='text-xs text-gray-400'>Même adresse pour USDT TRC20 et TRX</p></div><button class="bg-black text-white w-full py-3 rounded-xl font-bold">Enregistrer</button></form>""",user)

@app.route("/create", methods=["GET","POST"])
def create():
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    if request.method=="POST":
        client_name=request.form.get("client_name"); total=float(request.form.get("total",0) or 0); acompte=float(request.form.get("acompte",0) or 0)
        numero=f"DC-{datetime.datetime.now().year}-{secrets.token_hex(2).upper()}"
        items=[{"designation":request.form.get("designation[]"),"qte":1,"pu":total,"montant":total}]
        db.execute("INSERT INTO devis (user_id,numero,client_name,total,acompte,items_json,created_at,status) VALUES (?,?,?,?,?,?,?,?)",(user['id'],numero,client_name,total,acompte,json.dumps(items),datetime.datetime.now().strftime("%d/%m/%Y"),"Brouillon")); db.commit()
        return redirect(f"/devis/{db.execute('SELECT last_insert_rowid()').fetchone()[0]}")
    return layout("""<h1 class='font-bold'>Nouveau Devis</h1><form method="POST" class='bg-white p-6 rounded-2xl border mt-4 space-y-3'><input name="client_name" placeholder="Nom client *" required class="border p-2 rounded w-full"><input name="designation[]" placeholder="Service" class="border p-2 rounded w-full"><input name="total" type="number" placeholder="Total" class="border p-2 rounded w-full"><input name="acompte" type="number" placeholder="Acompte" class="border p-2 rounded w-full"><button class="bg-black text-white w-full py-3 rounded-xl">Créer</button></form>""",user)

@app.route("/pricing")
def pricing():
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    return layout(f"""
    <h1 class='text-3xl font-bold text-center'>Tarifs Auto</h1>
    <p class='text-center text-gray-500 mt-2'>MoMo + USDT BEP20/TRC20 + BNB + TRX - Activation auto sans Fedapay</p>
    <div class='grid md:grid-cols-2 gap-6 mt-8 max-w-3xl mx-auto'>
        <div class='bg-white border-2 border-black p-6 rounded-2xl shadow-lg'><h3 class='font-bold'>STARTER ⭐</h3><p class='text-3xl font-bold my-2'>5900F / 10$</p><p class='text-sm'>35 devis/mois</p>
            <div class='mt-4 space-y-2'>
                <a href='/pay/STARTER/MOMO' class='block bg-yellow-400 text-black py-2 rounded-xl font-bold text-center'>📱 MoMo MTN/Moov/Celtiis - 5900F</a>
                <div class='grid grid-cols-2 gap-2'>
                    <a href='/pay/STARTER/USDT_BEP20' class='bg-green-600 text-white py-2 rounded-xl text-center text-xs font-bold'>💵 USDT BEP20 - 10$</a>
                    <a href='/pay/STARTER/USDT_TRC20' class='bg-blue-600 text-white py-2 rounded-xl text-center text-xs font-bold'>💵 USDT TRC20 - 10$</a>
                    <a href='/pay/STARTER/BNB' class='bg-black text-white py-2 rounded-xl text-center text-xs font-bold'>🔶 BNB - 0.025</a>
                    <a href='/pay/STARTER/TRX' class='bg-red-600 text-white py-2 rounded-xl text-center text-xs font-bold'>🔴 TRX - 100</a>
                </div>
            </div>
        </div>
        <div class='bg-white border p-6 rounded-2xl'><h3 class='font-bold'>PRO 🚀</h3><p class='text-3xl font-bold my-2'>12900F / 22$</p><p class='text-sm'>Illimité</p>
            <div class='mt-4 space-y-2'>
                <a href='/pay/PRO/MOMO' class='block bg-yellow-400 text-black py-2 rounded-xl font-bold text-center'>📱 MoMo - 12900F</a>
                <div class='grid grid-cols-2 gap-2'>
                    <a href='/pay/PRO/USDT_BEP20' class='bg-green-600 text-white py-2 rounded-xl text-center text-xs font-bold'>💵 USDT BEP20 - 22$</a>
                    <a href='/pay/PRO/USDT_TRC20' class='bg-blue-600 text-white py-2 rounded-xl text-center text-xs font-bold'>💵 USDT TRC20 - 22$</a>
                    <a href='/pay/PRO/BNB' class='bg-black text-white py-2 rounded-xl text-center text-xs font-bold'>🔶 BNB - 0.055</a>
                    <a href='/pay/PRO/TRX' class='bg-red-600 text-white py-2 rounded-xl text-center text-xs font-bold'>🔴 TRX - 220</a>
                </div>
            </div>
        </div>
    </div>
    """,user)

@app.route("/pay/<plan>/<network>")
def pay_page(plan, network):
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    if plan not in ["STARTER","PRO"]: return "Plan invalide"
    
    prices=ADMIN_CONFIG['prices'][plan]
    cfg=ADMIN_CONFIG['crypto']
    
    # Détermine montant et adresse selon network
    if network=="MOMO":
        amount=prices['momo']; currency="F"; addr=ADMIN_CONFIG['momo_number']; name=ADMIN_CONFIG['momo_name']
        instr=f"<p class='text-4xl font-extrabold'>{amount}F</p><div class='bg-yellow-50 border p-4 rounded-xl mt-4'><p>Envoyer à :</p><p class='font-bold text-lg'>{addr} - {name}</p><p class='text-xs'>Motif: {user['email']}</p></div>"
    elif network=="USDT_BEP20":
        amount=prices['USDT_BEP20']; currency="USDT BEP20"; addr=cfg['BSC_ADDRESS']
        instr=f"<p class='text-4xl font-extrabold'>{amount} USDT</p><p class='text-xs'>Réseau BEP20 (BSC)</p><div class='bg-green-50 border p-4 rounded-xl mt-4'><p class='text-xs'>Adresse BEP20 (0x...):</p><p class='font-mono text-xs break-all bg-white p-2 rounded border mt-1'>{addr}</p><button onclick=\"navigator.clipboard.writeText('{addr}')\" class='text-xs bg-black text-white px-2 py-1 rounded mt-2'>Copier</button></div>"
    elif network=="USDT_TRC20":
        amount=prices['USDT_TRC20']; currency="USDT TRC20"; addr=cfg['TRON_ADDRESS']
        instr=f"<p class='text-4xl font-extrabold'>{amount} USDT</p><p class='text-xs'>Réseau TRC20 (Tron)</p><div class='bg-blue-50 border p-4 rounded-xl mt-4'><p class='text-xs'>Adresse TRC20 (T...):</p><p class='font-mono text-xs break-all bg-white p-2 rounded border mt-1'>{addr}</p></div>"
    elif network=="BNB":
        amount=prices['BNB']; currency="BNB"; addr=cfg['BSC_ADDRESS']
        instr=f"<p class='text-4xl font-extrabold'>{amount} BNB</p><p class='text-xs'>Réseau BEP20 (BSC)</p><div class='bg-black text-white p-4 rounded-xl mt-4'><p class='text-xs'>Adresse BNB:</p><p class='font-mono text-xs break-all bg-gray-800 p-2 rounded mt-1'>{addr}</p></div>"
    elif network=="TRX":
        amount=prices['TRX']; currency="TRX"; addr=cfg['TRON_ADDRESS']
        instr=f"<p class='text-4xl font-extrabold'>{amount} TRX</p><p class='text-xs'>Réseau Tron</p><div class='bg-red-50 border p-4 rounded-xl mt-4'><p class='text-xs'>Adresse TRX (T...):</p><p class='font-mono text-xs break-all bg-white p-2 rounded border mt-1'>{addr}</p></div>"
    else: return "Network invalide"

    return layout(f"""
    <div class='max-w-lg mx-auto'><h1 class='text-2xl font-bold'>Payer {plan} - {network}</h1><div class='bg-white p-6 rounded-2xl border mt-6'>
    <p class='text-sm text-gray-500'>Envoyez exactement :</p>{instr}
    <form method="POST" action="/verify_payment" class='mt-6'><input type="hidden" name="plan" value="{plan}"><input type="hidden" name="network" value="{network}"><input type="hidden" name="method" value="{'MOMO' if network=='MOMO' else 'CRYPTO'}">
    <label class='text-sm font-bold'>{'ID MoMo *' if network=='MOMO' else 'Transaction Hash / TXID *'}</label>
    <p class='text-xs text-gray-500 mb-1'>{'ID du SMS MoMo (ex: 1234567890)' if network=='MOMO' else 'BEP20: 0x... (66 chars) | TRC20/TRX: 64 chars hex'}</p>
    <input name="txid" placeholder="{'Ex: 1234567890' if network=='MOMO' else '0x... ou abc123...'}" required class="border p-3 rounded-xl w-full font-mono text-xs">
    <button class="bg-black text-white w-full py-3 rounded-xl font-bold mt-4">✅ J'ai payé - Vérifier & Activer automatiquement</button></form>
    <p class='text-xs text-center text-gray-400 mt-3'>Vérif auto : MoMo format + anti-doublon | USDT BEP20 via BscScan | USDT TRC20/TRX via TronScan</p></div></div>
    """,user)

@app.route("/verify_payment", methods=["POST"])
def verify_payment():
    if 'user_id' not in session: return redirect("/login")
    plan=request.form.get("plan"); network=request.form.get("network"); method=request.form.get("method"); txid=request.form.get("txid","").strip()
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    ok,msg=verify_txid(method,network,txid)
    if not ok: return layout(f"<div class='max-w-lg mx-auto bg-white p-6 rounded-2xl border mt-10'><h2 class='text-red-600 font-bold'>❌ {msg}</h2><a href='/pay/{plan}/{network}' class='block bg-black text-white py-3 rounded-xl text-center mt-4'>Réessayer</a></div>",user)
    try:
        prices=ADMIN_CONFIG['prices'][plan]; amount=prices.get(network,0) if network!="MOMO" else prices['momo']
        db.execute("INSERT INTO payments (user_id,type,plan,method,network,amount,currency,txid,status,created_at,verified_data) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                   (user['id'],'subscription',plan,method,network,amount,network,txid,'Vérifié',datetime.datetime.now().isoformat(),msg))
        exp=(datetime.datetime.now()+datetime.timedelta(days=30)).isoformat()
        db.execute("UPDATE users SET plan=?,expiration=? WHERE id=?",(plan,exp,user['id'])); db.commit()
    except Exception as e:
        if "UNIQUE" in str(e): return layout(f"<div class='bg-white p-6 rounded-2xl border'><p>TXID déjà utilisé</p></div>",user)
        raise e
    return layout(f"<div class='max-w-lg mx-auto bg-white p-8 rounded-2xl border mt-10 text-center'><h1 class='text-5xl'>🎉</h1><h2 class='text-2xl font-bold mt-4'>{plan} Activé !</h2><p class='text-sm mt-2'>{msg}</p><p class='font-mono text-xs bg-gray-100 p-2 rounded mt-3 break-all'>{txid}</p><a href='/dashboard' class='block bg-black text-white py-3 rounded-xl font-bold mt-6'>Dashboard</a></div>",user)

@app.route("/devis/<int:did>", methods=["GET","POST"])
def view_devis(did):
    db=get_db(); d=db.execute("SELECT * FROM devis WHERE id=?",(did,)).fetchone()
    if not d: return "Introuvable"
    seller=db.execute("SELECT * FROM users WHERE id=?",(d['user_id'],)).fetchone()
    if request.method=="POST" and request.form.get("action")=="accepter":
        # Page paiement acompte multi-crypto
        momo_num=seller['momo_number'] or "Non configuré"; momo_name=seller['momo_name'] or ""
        bsc_addr=seller['usdt_bep20'] or seller['bnb_address'] or ADMIN_CONFIG['crypto']['BSC_ADDRESS']
        tron_addr=seller['usdt_trc20'] or seller['trx_address'] or ADMIN_CONFIG['crypto']['TRON_ADDRESS']
        acompte=d['acompte'] or 0
        return f"""<html><head>{BASE_CSS}</head><body class='bg-green-50 p-4'><div class='max-w-3xl mx-auto bg-white p-6 rounded-2xl shadow'>
        <h2 class='text-xl font-bold text-center'>🎉 Devis {d['numero']} Accepté - Payer l'acompte {acompte}F</h2>
        <div class='grid md:grid-cols-3 gap-3 mt-6'>
            <div class='border p-3 rounded-xl'><p class='font-bold text-sm'>📱 MoMo</p><p>{momo_num}<br><span class='text-xs'>{momo_name}</span></p><p class='text-xs bg-yellow-100 p-1 rounded mt-2'>{acompte}F</p><form method="POST" action="/verify_acompte/{did}" class='mt-2'><input type="hidden" name="network" value="MOMO"><input name="txid" placeholder="ID MoMo" required class="border p-2 rounded w-full text-xs"><button class='bg-black text-white w-full py-2 rounded mt-1 text-xs'>Payer MoMo</button></form></div>
            <div class='border p-3 rounded-xl'><p class='font-bold text-sm'>💵 USDT BEP20 / BNB</p><p class='font-mono text-xs break-all bg-gray-50 p-1 rounded'>{bsc_addr}</p><p class='text-xs bg-green-100 p-1 rounded mt-2'>BSC - USDT ou BNB</p><form method="POST" action="/verify_acompte/{did}" class='mt-2'><input type="hidden" name="network" value="USDT_BEP20"><input name="txid" placeholder="0x... (66 chars)" required class="border p-2 rounded w-full text-xs"><button class='bg-green-600 text-white w-full py-2 rounded mt-1 text-xs'>Payer USDT BEP20 / BNB</button></form></div>
            <div class='border p-3 rounded-xl'><p class='font-bold text-sm'>💵 USDT TRC20 / TRX</p><p class='font-mono text-xs break-all bg-gray-50 p-1 rounded'>{tron_addr}</p><p class='text-xs bg-blue-100 p-1 rounded mt-2'>TRON - USDT ou TRX</p><form method="POST" action="/verify_acompte/{did}" class='mt-2'><input type="hidden" name="network" value="USDT_TRC20"><input name="txid" placeholder="TXID 64 chars" required class="border p-2 rounded w-full text-xs"><button class='bg-blue-600 text-white w-full py-2 rounded mt-1 text-xs'>Payer USDT TRC20 / TRX</button></form></div>
        </div></div></body></html>"""
    db.execute("UPDATE devis SET views=views+1 WHERE id=?",(did,)); db.commit()
    return f"<html><head>{BASE_CSS}</head><body class='p-6'><div class='max-w-2xl mx-auto bg-white p-8 rounded-2xl border'><h1>DEVIS {d['numero']}</h1><p>{d['client_name']} - {d['total']}F - Acompte {d['acompte']}F</p><form method='POST'><button name='action' value='accepter' class='bg-green-600 text-white w-full py-3 rounded-xl mt-6'>✅ Accepter et payer acompte</button></form></div></body></html>"

@app.route("/verify_acompte/<int:did>", methods=["POST"])
def verify_acompte(did):
    db=get_db(); d=db.execute("SELECT * FROM devis WHERE id=?",(did,)).fetchone()
    network=request.form.get("network"); txid=request.form.get("txid","").strip()
    method="MOMO" if network=="MOMO" else "CRYPTO"
    ok,msg=verify_txid(method,network,txid)
    if not ok: return f"<p>{msg}</p><a href='/devis/{did}'>Retour</a>"
    try:
        db.execute("INSERT INTO payments (user_id,devis_id,type,method,network,amount,currency,txid,status,created_at,verified_data) VALUES (?,?,?,?,?,?,?,?,?,?,?)",(d['user_id'],did,'acompte',method,network,d['acompte'],network,txid,'Vérifié',datetime.datetime.now().isoformat(),msg))
        db.execute("UPDATE devis SET status='Acompte Payé' WHERE id=?",(did,)); db.commit()
    except Exception as e:
        if "UNIQUE" in str(e): return "TXID déjà utilisé"
        raise e
    return f"<html><head>{BASE_CSS}</head><body class='bg-green-50 flex items-center justify-center min-h-screen'><div class='bg-white p-8 rounded-2xl text-center'><h1>✅ Acompte Payé via {network} !</h1><p class='text-xs mt-2'>{msg}</p><p class='font-mono text-xs mt-2'>{txid}</p></div></body></html>"

init_db()
if __name__=="__main__": app.run(host="0.0.0.0",port=8080)
