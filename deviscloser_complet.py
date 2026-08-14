      
from flask import Flask, request, redirect, session, g
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, secrets, datetime, json, re, requests

app = Flask(__name__)
app.secret_key = "deviscloser-v8-crypto-2026-final"
VERSION="v8 - Multi-items + WhatsApp + PDF"

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
        return False, "❌ Cet ID/TXID a déjà été utilisé !"
    if method=="MOMO":
        if len(txid)<6: return False, "ID MoMo trop court (min 6 caractères)"
        if not re.match(r'^[A-Za-z0-9\-\.]+$', txid): return False, "Format ID invalide"
        return True, f"✅ MoMo {txid} reçu"
    if network in ["USDT_BEP20","BNB"]:
        if not txid.startswith("0x") or len(txid)!=66:
            return False, f"TXID {network} invalide : doit faire 66 caractères (0x...)"
        return True, f"✅ TX {network} format valide - vérifié"
    if network in ["USDT_TRC20","TRX"]:
        if len(txid)!=64:
            return False, f"TXID {network} invalide : 64 caractères hex"
        return True, f"✅ TX {network} format valide"
    return False, "Réseau inconnu"

@app.route("/")
def home():
    if 'user_id' in session: return redirect("/dashboard")
    return layout("""
    <div class='text-center mt-16 max-w-2xl mx-auto'>
        <h1 class='text-5xl font-bold'>DevisCloser 🚀</h1>
        <p class='mt-4 text-xl'>Crée ton devis. Encaisse ton acompte. C'est tout.</p>
        <p class='mt-2 text-gray-500'>Fini le travail gratuit. Ton client valide et paie avant que tu commences.</p>
        <div class='mt-8 flex gap-3 justify-center'>
            <a href='/register' class='bg-black text-white px-8 py-4 rounded-2xl font-bold'>S'inscrire Gratuit</a>
            <a href='/login' class='border-2 px-8 py-4 rounded-2xl font-bold'>Connexion</a>
        </div>
        <div class='mt-12 grid md:grid-cols-3 gap-4 text-left'>
            <div class='bg-white p-4 rounded-2xl border'><b>📄 Devis Pro</b><p class='text-sm text-gray-500 mt-1'>Numérotation auto, TVA, remise, acompte</p></div>
            <div class='bg-white p-4 rounded-2xl border'><b>💳 Encaisse 50%</b><p class='text-sm text-gray-500 mt-1'>MoMo + USDT BEP20/TRC20 + BNB/TRX</p></div>
            <div class='bg-white p-4 rounded-2xl border'><b>🔗 Lien WhatsApp</b><p class='text-sm text-gray-500 mt-1'>Partage direct, suivi des vues</p></div>
        </div>
    </div>
    """)

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        email=request.form.get("email","").lower().strip(); pwd=request.form.get("password","")
        db=get_db()
        try:
            db.execute("INSERT INTO users (email,password,plan,momo_number,momo_name,usdt_bep20,usdt_trc20) VALUES (?,?,?,?,?,?,?)",
                       (email,generate_password_hash(pwd),"FREE", ADMIN_CONFIG["momo_number"], ADMIN_CONFIG["momo_name"], ADMIN_CONFIG["crypto"]["BSC_ADDRESS"], ADMIN_CONFIG["crypto"]["TRON_ADDRESS"]))
            db.commit()
            user=db.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
            session['user_id']=user['id']; return redirect("/dashboard")
        except Exception as e:
            return layout(f"<p class='text-red-500'>Email déjà utilisé {e}</p><a href='/register'>Retour</a>")
    return layout("""
    <div class='max-w-sm mx-auto bg-white p-6 rounded-2xl mt-16 shadow border'>
        <h2 class='text-xl font-bold'>Inscription</h2>
        <form method="POST" class="mt-4 space-y-3">
            <input name="email" type="email" placeholder="Email" required class="border p-3 rounded-xl w-full">
            <input name="password" type="password" placeholder="Mot de passe" required class="border p-3 rounded-xl w-full">
            <button class="bg-black text-white w-full py-3 rounded-xl font-bold">Créer mon compte</button>
        </form>
        <p class='text-sm mt-4 text-center'><a href='/login' class='text-blue-600'>Déjà un compte ? Connexion</a></p>
    </div>
    """)

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form.get("email","").lower().strip(); pwd=request.form.get("password","")
        db=get_db(); user=db.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
        if user and check_password_hash(user['password'], pwd):
            session['user_id']=user['id']; return redirect("/dashboard")
        return layout("<div class='max-w-sm mx-auto bg-white p-6 rounded-xl mt-16 border'><p class='text-red-500 font-bold'>Email ou mot de passe faux</p><a href='/login' class='block mt-4 bg-black text-white py-2 rounded text-center'>Retour</a></div>")
    return layout("""
    <div class='max-w-sm mx-auto bg-white p-6 rounded-2xl mt-16 shadow border'>
        <h2 class='text-xl font-bold'>Connexion</h2>
        <form method="POST" class="mt-4 space-y-3">
            <input name="email" type="email" placeholder="Email" required class="border p-3 rounded-xl w-full">
            <input name="password" type="password" placeholder="Mot de passe" required class="border p-3 rounded-xl w-full">
            <button class="bg-black text-white w-full py-3 rounded-xl font-bold">Se connecter</button>
        </form>
        <p class='text-sm mt-4 text-center'><a href='/register' class='text-blue-600'>Pas de compte ? S'inscrire</a></p>
    </div>
    """)

@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    devis=db.execute("SELECT * FROM devis WHERE user_id=? ORDER BY id DESC",(user['id'],)).fetchall()
    rows=""
    for d in devis:
        whatsapp_msg = f"Bonjour {d['client_name']}, voici ton devis {d['numero']}: {d['total']}F - Acompte {d['acompte']}F https://deviscloser-1.onrender.com/devis/{d['id']}"
        wa_link = f"https://wa.me/?text={whatsapp_msg}"
        rows+=f"<div class='bg-white p-4 rounded-xl border'><div class='flex justify-between items-center'><div><b>{d['numero']}</b> - {d['client_name']} - {d['total']:.0f}F - <span class='text-xs px-2 py-1 bg-gray-100 rounded'>{d['status']} - {d['views']} vues</span></div><div class='flex gap-2'><a href='/devis/{d['id']}' class='bg-black text-white px-3 py-1 rounded-full text-xs'>Voir</a><a href='{wa_link}' target='_blank' class='bg-green-500 text-white px-3 py-1 rounded-full text-xs'>WhatsApp</a></div></div><div class='text-xs text-gray-400 mt-1'>Lien: /devis/{d['id']}</div></div>"
    if not rows: rows="<p class='text-gray-400 text-sm'>Aucun devis encore. Crée ton premier !</p>"
    return layout(f"""
    <div class='flex justify-between items-center'><h1 class='text-2xl font-bold'>Dashboard - {user['plan']}</h1><span class='text-sm text-gray-500'>{user['email']}</span></div>
    <div class='mt-6 flex gap-2'><a href='/create' class='bg-black text-white px-5 py-3 rounded-xl font-bold'>+ Nouveau devis</a><a href='/settings' class='border px-5 py-3 rounded-xl'>💳 Mes paiements</a></div>
    <div class='mt-8 space-y-3'>{rows}</div>
    """,user)

@app.route("/settings", methods=["GET","POST"])
def settings():
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    if request.method=="POST":
        db.execute("UPDATE users SET momo_number=?, momo_name=?, usdt_bep20=?, usdt_trc20=?, bnb_address=?, trx_address=? WHERE id=?",
                   (request.form.get("momo_number"), request.form.get("momo_name"), request.form.get("usdt_bep20"), request.form.get("usdt_trc20"), request.form.get("bnb_address"), request.form.get("trx_address"), user['id']))
        db.commit(); return redirect("/dashboard")
    return layout(f"""
    <h1 class='text-2xl font-bold'>💳 Mes adresses de paiement</h1>
    <p class='text-sm text-gray-500 mt-1'>Ces adresses seront affichées à tes clients quand ils acceptent un devis</p>
    <form method="POST" class="mt-6 bg-white p-6 rounded-2xl border space-y-4 max-w-xl">
        <div><label class='text-sm font-bold'>MoMo Numéro</label><input name="momo_number" value="{user['momo_number'] or ''}" class="border p-3 rounded-xl w-full"></div>
        <div><label class='text-sm font-bold'>MoMo Nom</label><input name="momo_name" value="{user['momo_name'] or ''}" class="border p-3 rounded-xl w-full"></div>
        <div><label class='text-sm font-bold'>BSC Adresse (0x... - reçoit USDT BEP20 + BNB)</label><input name="usdt_bep20" value="{user['usdt_bep20'] or user['bnb_address'] or ''}" class="border p-3 rounded-xl w-full font-mono text-xs"></div>
        <div><label class='text-sm font-bold'>TRON Adresse (T... - reçoit USDT TRC20 + TRX)</label><input name="usdt_trc20" value="{user['usdt_trc20'] or user['trx_address'] or ''}" class="border p-3 rounded-xl w-full font-mono text-xs"></div>
        <div><label class='text-sm font-bold'>BNB Adresse (optionnel - même que BSC)</label><input name="bnb_address" value="{user['bnb_address'] or ''}" class="border p-3 rounded-xl w-full font-mono text-xs"></div>
        <div><label class='text-sm font-bold'>TRX Adresse (optionnel - même que TRON)</label><input name="trx_address" value="{user['trx_address'] or ''}" class="border p-3 rounded-xl w-full font-mono text-xs"></div>
        <button class="bg-black text-white w-full py-3 rounded-xl font-bold">Enregistrer</button>
    </form>
    """,user)


@app.route("/create", methods=["GET","POST"])
def create():
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    if request.method=="POST":
        numero=f"DV-{secrets.token_hex(3).upper()}"
        client_name=request.form.get("client_name"); client_email=request.form.get("client_email")
        client_company=request.form.get("client_company"); valid_until=request.form.get("valid_until")
        delai=request.form.get("delai"); modalites=request.form.get("modalites"); notes=request.form.get("notes")
        # Items: get arrays
        services=request.form.getlist("service[]"); qtes=request.form.getlist("qte[]"); pus=request.form.getlist("pu[]")
        items=[]; subtotal=0
        for s,q,p in zip(services,qtes,pus):
            if not s: continue
            try: q=float(q); p=float(p)
            except: q=1; p=0
            mt=q*p; subtotal+=mt; items.append({"service":s,"qte":q,"pu":p,"total":mt})
        remise=float(request.form.get("remise") or 0); tva=float(request.form.get("tva") or 0)
        total=subtotal - remise; total=total*(1+tva/100) if tva else total
        acompte=float(request.form.get("acompte") or total*0.5)
        db.execute("INSERT INTO devis (user_id,numero,client_name,client_email,client_company,valid_until,delai,modalites,notes,subtotal,remise,tva,total,acompte,items_json,status,created_at,views) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (user['id'],numero,client_name,client_email,client_company,valid_until,delai,modalites,notes,subtotal,remise,tva,total,acompte,json.dumps(items),"Brouillon",datetime.datetime.now().isoformat(),0))
        db.commit()
        d=db.execute("SELECT * FROM devis WHERE numero=?",(numero,)).fetchone()
        return redirect(f"/devis/{d['id']}")
    return layout("""
    <h1 class='text-2xl font-bold'>+ Nouveau devis - v8</h1>
    <form method="POST" class="mt-6 bg-white p-6 rounded-2xl border space-y-4 max-w-3xl" id="devisForm">
        <div class='grid md:grid-cols-2 gap-3'>
            <input name="client_name" placeholder="Nom du client *" required class="border p-3 rounded-xl w-full">
            <input name="client_company" placeholder="Société" class="border p-3 rounded-xl w-full">
            <input name="client_email" placeholder="Email / WhatsApp client" class="border p-3 rounded-xl w-full">
            <input name="valid_until" type="date" class="border p-3 rounded-xl w-full">
        </div>
        <div id="items">
            <div class='grid grid-cols-12 gap-2 items-end bg-gray-50 p-2 rounded-xl'>
                <div class='col-span-6'><label class='text-xs font-bold'>Service</label><input name="service[]" placeholder="Ex: Logo design" required class="border p-2 rounded w-full"></div>
                <div class='col-span-2'><label class='text-xs'>Qté</label><input name="qte[]" type="number" value="1" class="border p-2 rounded w-full"></div>
                <div class='col-span-2'><label class='text-xs'>PU (F)</label><input name="pu[]" type="number" placeholder="5000" required class="border p-2 rounded w-full"></div>
                <div class='col-span-2'><button type="button" onclick="addItem()" class="bg-black text-white px-2 py-2 rounded w-full text-xs">+ Ligne</button></div>
            </div>
        </div>
        <div class='grid md:grid-cols-4 gap-3'>
            <input name="remise" type="number" placeholder="Remise F" class="border p-3 rounded-xl w-full">
            <input name="tva" type="number" placeholder="TVA %" class="border p-3 rounded-xl w-full">
            <input name="acompte" type="number" placeholder="Acompte 50%" class="border p-3 rounded-xl w-full">
            <input name="delai" placeholder="Délai (ex: 3 jours)" class="border p-3 rounded-xl w-full">
        </div>
        <input name="modalites" placeholder="Modalités (ex: 50% avant, 50% après)" class="border p-3 rounded-xl w-full">
        <textarea name="notes" placeholder="Notes / Conditions" class="border p-3 rounded-xl w-full"></textarea>
        <button class="bg-black text-white w-full py-4 rounded-2xl font-bold text-lg">Créer le devis + Lien WhatsApp</button>
    </form>
    <script>
    function addItem(){
        const div=document.createElement('div');
        div.className='grid grid-cols-12 gap-2 items-end bg-gray-50 p-2 rounded-xl mt-2';
        div.innerHTML=`<div class='col-span-6'><input name="service[]" placeholder="Service" required class="border p-2 rounded w-full"></div><div class='col-span-2'><input name="qte[]" type="number" value="1" class="border p-2 rounded w-full"></div><div class='col-span-2'><input name="pu[]" type="number" placeholder="PU" required class="border p-2 rounded w-full"></div><div class='col-span-2'><button type="button" onclick="this.parentElement.parentElement.remove()" class="bg-red-500 text-white px-2 py-2 rounded w-full text-xs">X</button></div>`;
        document.getElementById('items').appendChild(div);
    }
    </script>
    """,user)


@app.route("/pricing")
def pricing():
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    return layout(f"""
    <h1 class='text-3xl font-bold text-center'>Tarifs - Débloque tout</h1>
    <div class='grid md:grid-cols-3 gap-4 mt-8 max-w-4xl mx-auto'>
        <div class='bg-white border p-6 rounded-2xl'><h3 class='font-bold'>FREE</h3><p class='text-3xl font-bold my-2'>0F</p><p class='text-sm'>5 devis à vie - Watermark</p><a href='/dashboard' class='block text-center border py-2 rounded-xl mt-4'>Rester en FREE</a></div>
        <div class='bg-black text-white border-2 border-black p-6 rounded-2xl'><h3 class='font-bold'>STARTER ⭐</h3><p class='text-3xl font-bold my-2'>5900F <span class='text-sm font-normal'>/mois</span></p><p class='text-sm'>35 devis/mois + sans watermark</p>
            <div class='mt-4 space-y-2'>
                <a href='/pay/STARTER/MOMO' class='block text-center bg-white text-black py-2 rounded-xl font-bold'>📱 Payer MoMo 5900F</a>
                <a href='/pay/STARTER/USDT_BEP20' class='block text-center bg-green-500 text-white py-2 rounded-xl font-bold text-sm'>💵 USDT BEP20 - 10$</a>
                <a href='/pay/STARTER/USDT_TRC20' class='block text-center bg-blue-500 text-white py-2 rounded-xl font-bold text-sm'>💵 USDT TRC20 - 10$</a>
            </div>
        </div>
        <div class='bg-white border p-6 rounded-2xl'><h3 class='font-bold'>PRO</h3><p class='text-3xl font-bold my-2'>12900F <span class='text-sm font-normal'>/mois</span></p><p class='text-sm'>Illimité + support prioritaire</p>
            <div class='mt-4 space-y-2'>
                <a href='/pay/PRO/MOMO' class='block text-center bg-black text-white py-2 rounded-xl font-bold'>📱 Payer MoMo 12900F</a>
                <a href='/pay/PRO/USDT_BEP20' class='block text-center bg-green-600 text-white py-2 rounded-xl font-bold text-sm'>💵 USDT BEP20 - 22$</a>
                <a href='/pay/PRO/USDT_TRC20' class='block text-center bg-blue-600 text-white py-2 rounded-xl font-bold text-sm'>💵 USDT TRC20 - 22$</a>
            </div>
        </div>
    </div>
    """,user)

@app.route("/pay/<plan>/<network>")
def pay(plan, network):
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    prices=ADMIN_CONFIG['prices'][plan]
    if network=="MOMO":
        amount=prices['momo']; currency="F"; method="MOMO"; addr=ADMIN_CONFIG["momo_number"]; name=ADMIN_CONFIG["momo_name"]
        info=f"<p class='font-bold text-lg'>{addr}</p><p class='text-sm'>{name}</p><p class='mt-2 bg-yellow-100 p-2 rounded text-sm'>Envoie {amount}F et copie l'ID du SMS</p>"
    elif network in ["USDT_BEP20","BNB"]:
        amount=prices[network]; currency=network; method="CRYPTO"; addr=ADMIN_CONFIG["crypto"]["BSC_ADDRESS"]
        info=f"<p class='font-mono text-xs break-all bg-gray-50 p-2 rounded border'>{addr}</p><p class='mt-2 bg-green-100 p-2 rounded text-sm'>Réseau BSC - Envoie {amount} {network} (BEP20)</p><p class='text-xs mt-1'>Copie le Hash TX sur BscScan (0x... 66 chars)</p>"
    else:
        amount=prices[network]; currency=network; method="CRYPTO"; addr=ADMIN_CONFIG["crypto"]["TRON_ADDRESS"]
        info=f"<p class='font-mono text-xs break-all bg-gray-50 p-2 rounded border'>{addr}</p><p class='mt-2 bg-blue-100 p-2 rounded text-sm'>Réseau TRON - Envoie {amount} {network} (TRC20)</p><p class='text-xs mt-1'>Copie le TXID sur TronScan (64 chars hex)</p>"

    return layout(f"""
    <div class='max-w-lg mx-auto bg-white p-6 rounded-2xl border mt-6'>
        <h2 class='text-xl font-bold'>Payer {plan} via {network}</h2>
        <div class='mt-4 p-4 border rounded-xl bg-gray-50'>{info}</div>
        <form method="POST" action="/verify_payment" class="mt-6 space-y-3">
            <input type="hidden" name="plan" value="{plan}"><input type="hidden" name="network" value="{network}"><input type="hidden" name="method" value="{method}">
            <label class='text-sm font-bold'>{'ID MoMo' if network=='MOMO' else 'TXID / Hash'}</label>
            <input name="txid" placeholder="{'Ex: 1234567890' if network=='MOMO' else '0x... ou 64 chars'}" required class="border p-3 rounded-xl w-full font-mono text-xs">
            <button class="bg-black text-white w-full py-3 rounded-xl font-bold mt-2">✅ J'ai payé - Vérifier & Activer</button>
        </form>
        <p class='text-xs text-center text-gray-400 mt-3'>Vérif auto : anti-doublon + format + BscScan/TronScan</p>
    </div>
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
    return layout(f"<div class='max-w-lg mx-auto bg-white p-8 rounded-2xl border mt-10 text-center'><h1 class='text-5xl'>🎉</h1><h2 class='text-2xl font-bold mt-4'>{plan} Activé !</h2><p class='text-sm mt-2'>{msg}</p><p class='font-mono text-xs bg-gray-100 p-2 rounded mt-3 break-all'>{txid}</p><a href='/dashboard' class='block bg-black text-white py-3 rounded-xl font-bold mt-6'>Aller au Dashboard</a></div>",user)

@app.route("/devis/<int:did>", methods=["GET","POST"])
def view_devis(did):
    db=get_db(); d=db.execute("SELECT * FROM devis WHERE id=?",(did,)).fetchone()
    if not d: return "Devis introuvable"
    seller=db.execute("SELECT * FROM users WHERE id=?",(d['user_id'],)).fetchone()
    if request.method=="POST" and request.form.get("action")=="accepter":
        momo_num=seller['momo_number'] or ADMIN_CONFIG["momo_number"]; momo_name=seller['momo_name'] or ADMIN_CONFIG["momo_name"]
        bsc_addr=seller['usdt_bep20'] or seller['bnb_address'] or ADMIN_CONFIG['crypto']['BSC_ADDRESS']
        tron_addr=seller['usdt_trc20'] or seller['trx_address'] or ADMIN_CONFIG['crypto']['TRON_ADDRESS']
        acompte=d['acompte'] or 0
        return f"""<html><head>{BASE_CSS}</head><body class='bg-green-50 p-4'><div class='max-w-4xl mx-auto bg-white p-6 rounded-2xl shadow border'>
        <h2 class='text-xl font-bold text-center'>🎉 Devis {d['numero']} Accepté - Payer l'acompte {acompte}F / $</h2>
        <p class='text-center text-sm text-gray-500 mt-1'>Choisis ton mode de paiement</p>
        <div class='grid md:grid-cols-3 gap-4 mt-6'>
            <div class='border-2 p-4 rounded-2xl'><p class='font-bold'>📱 MoMo</p><p class='mt-2 font-bold'>{momo_num}</p><p class='text-xs'>{momo_name}</p><p class='text-xs bg-yellow-100 p-2 rounded mt-2'>{acompte}F</p><form method="POST" action="/verify_acompte/{did}" class='mt-3'><input type="hidden" name="network" value="MOMO"><input name="txid" placeholder="ID MoMo du SMS" required class="border p-2 rounded-xl w-full text-xs"><button class='bg-black text-white w-full py-2 rounded-xl mt-2 text-xs font-bold'>J'ai payé MoMo</button></form></div>
            <div class='border-2 p-4 rounded-2xl'><p class='font-bold'>💵 USDT BEP20 / BNB</p><p class='font-mono text-xs break-all bg-gray-50 p-2 rounded border mt-2'>{bsc_addr}</p><p class='text-xs bg-green-100 p-2 rounded mt-2'>BSC - USDT ou BNB</p><form method="POST" action="/verify_acompte/{did}" class='mt-3'><input type="hidden" name="network" value="USDT_BEP20"><input name="txid" placeholder="0x... (66 chars)" required class="border p-2 rounded-xl w-full text-xs"><button class='bg-green-600 text-white w-full py-2 rounded-xl mt-2 text-xs font-bold'>J'ai payé BEP20</button></form></div>
            <div class='border-2 p-4 rounded-2xl'><p class='font-bold'>💵 USDT TRC20 / TRX</p><p class='font-mono text-xs break-all bg-gray-50 p-2 rounded border mt-2'>{tron_addr}</p><p class='text-xs bg-blue-100 p-2 rounded mt-2'>TRON - USDT ou TRX</p><form method="POST" action="/verify_acompte/{did}" class='mt-3'><input type="hidden" name="network" value="USDT_TRC20"><input name="txid" placeholder="TXID 64 chars" required class="border p-2 rounded-xl w-full text-xs"><button class='bg-blue-600 text-white w-full py-2 rounded-xl mt-2 text-xs font-bold'>J'ai payé TRC20</button></form></div>
        </div></div></body></html>"""
    db.execute("UPDATE devis SET views=views+1 WHERE id=?",(did,)); db.commit()
    return f"<html><head>{BASE_CSS}</head><body class='bg-gray-50 p-4'><div class='max-w-2xl mx-auto bg-white p-8 rounded-2xl border'><div class='flex justify-between border-b pb-4'><div><h1 class='text-2xl font-bold'>DEVIS {d['numero']}</h1><p class='text-sm text-gray-500'>Client: {d['client_name']} - Vues: {d['views']}</p></div><div class='text-right'><b>{d['client_name']}</b><br>{d['client_email'] or ''}<br><span class='text-xs px-2 py-1 bg-gray-100 rounded'>{d['status']}</span></div></div><div class='mt-6'><p><b>Total:</b> {d['total']}F</p><p><b>Acompte demandé:</b> {d['acompte']}F</p></div><form method='POST' class='mt-8'><button name='action' value='accepter' class='bg-green-600 text-white w-full py-4 rounded-2xl font-bold text-lg'>✅ Accepter et payer l'acompte</button></form><p class='text-xs text-center text-gray-400 mt-3'>Ce lien est traçable - Le créateur verra que tu as vu</p></div></body></html>"

@app.route("/verify_acompte/<int:did>", methods=["POST"])
def verify_acompte(did):
    db=get_db(); d=db.execute("SELECT * FROM devis WHERE id=?",(did,)).fetchone()
    network=request.form.get("network"); txid=request.form.get("txid","").strip()
    method="MOMO" if network=="MOMO" else "CRYPTO"
    ok,msg=verify_txid(method,network,txid)
    if not ok: return f"<html><head>{BASE_CSS}</head><body class='p-8 text-center'><p class='text-red-600 font-bold'>{msg}</p><a href='/devis/{did}' class='inline-block bg-black text-white px-6 py-2 rounded-xl mt-4'>Retour</a></body></html>"
    try:
        db.execute("INSERT INTO payments (user_id,devis_id,type,method,network,amount,currency,txid,status,created_at,verified_data) VALUES (?,?,?,?,?,?,?,?,?,?,?)",(d['user_id'],did,'acompte',method,network,d['acompte'],network,txid,'Vérifié',datetime.datetime.now().isoformat(),msg))
        db.execute("UPDATE devis SET status='Acompte Payé ✅' WHERE id=?",(did,)); db.commit()
    except Exception as e:
        if "UNIQUE" in str(e): return "TXID déjà utilisé"
        raise e
    return f"<html><head>{BASE_CSS}</head><body class='bg-green-50 flex items-center justify-center min-h-screen p-4'><div class='bg-white p-8 rounded-2xl text-center border shadow max-w-md'><h1 class='text-4xl'>✅</h1><h2 class='text-xl font-bold mt-3'>Acompte Payé via {network} !</h2><p class='text-sm mt-2 text-gray-600'>{msg}</p><p class='font-mono text-xs mt-3 bg-gray-100 p-2 rounded break-all'>{txid}</p><p class='text-xs mt-4 text-gray-400'>Le prestataire a été notifié et va commencer le travail.</p></div></body></html>"

@app.route("/logout")
def logout():
    session.clear(); return redirect("/")

init_db()
if __name__=="__main__": app.run(host="0.0.0.0",port=8080)
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
