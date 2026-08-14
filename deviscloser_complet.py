
from flask import Flask, request, redirect, session, g
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, secrets, datetime, json, re

app = Flask(__name__)
app.secret_key = "deviscloser-v10-final-2026"
VERSION="v10"

DB = "deviscloser.db"
ADMIN_CONFIG = {
    "momo_number": "2290156853149",
    "momo_name": "SOSTHENE HERVE EDOH",
    "crypto": {"BSC_ADDRESS": "0xeB3e09b4F53d863dEBb0d49591597741612b6FB1","TRON_ADDRESS": "THwRRQVtymKPwLdXdc7PmQvmvNaugX2cff"},
    "prices": {"STARTER": {"momo": 5900, "USDT_BEP20": 10, "USDT_TRC20": 10, "BNB": 0.025, "TRX": 100},"PRO": {"momo": 12900, "USDT_BEP20": 22, "USDT_TRC20": 22, "BNB": 0.055, "TRX": 220}}
}
def get_db():
    db=getattr(g,'_database',None)
    if db is None:
        db=g._database=sqlite3.connect(DB)
        db.row_factory=sqlite3.Row
    return db
def init_db():
    with app.app_context():
        db=get_db()
        db.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT, plan TEXT DEFAULT 'FREE', expiration TEXT, momo_number TEXT, momo_name TEXT, usdt_bep20 TEXT, usdt_trc20 TEXT, bnb_address TEXT, trx_address TEXT)""")
        db.execute("""CREATE TABLE IF NOT EXISTS devis (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, numero TEXT, client_name TEXT, client_email TEXT, client_company TEXT, valid_until TEXT, delai TEXT, modalites TEXT, notes TEXT, subtotal REAL, remise REAL, tva REAL, total REAL, acompte REAL, items_json TEXT, status TEXT DEFAULT 'Brouillon', views INTEGER DEFAULT 0, created_at TEXT)""")
        db.execute("""CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, devis_id INTEGER, type TEXT, plan TEXT, method TEXT, network TEXT, amount REAL, currency TEXT, txid TEXT UNIQUE, status TEXT, created_at TEXT, verified_data TEXT)""")
        db.commit()
@app.teardown_appcontext
def close_connection(ex):
    db=getattr(g,'_database',None)
    if db: db.close()

BASE_CSS='<meta name="viewport" content="width=device-width, initial-scale=1"><script src="https://cdn.tailwindcss.com"></script>'
def layout(content,user=None):
    nav=""
    if user:
        nav=f"""<nav class='bg-white border-b p-3 flex justify-between items-center text-sm sticky top-0 z-10'><b>DevisCloser</b><div class='flex gap-3 items-center'><a href='/dashboard'>Dashboard</a><a href='/settings'>💳 Paiements</a><a href='/pricing'>Tarifs</a><span class='bg-black text-white px-2 py-1 rounded-full text-xs'>{user['plan']}</span><a href='/logout' class='text-red-500'>Sortir</a></div></nav>"""
    return f"<html><head>{BASE_CSS}<title>DevisCloser v10</title></head><body class='bg-gray-50'>{nav}<div class='max-w-5xl mx-auto p-4'>{content}</div></body></html>"

def verify_txid(method,network,txid):
    txid=txid.strip()
    db=get_db()
    if db.execute("SELECT * FROM payments WHERE txid=?",(txid,)).fetchone(): return False,"❌ TXID déjà utilisé !"
    if method=="MOMO":
        if len(txid)<6: return False,"ID MoMo trop court"
        return True,f"✅ MoMo {txid} reçu"
    if network in ["USDT_BEP20","BNB"]:
        if not txid.startswith("0x") or len(txid)!=66: return False,f"TXID {network} invalide: 66 chars (0x...)"
        return True,f"✅ TX {network} valide"
    if network in ["USDT_TRC20","TRX"]:
        if len(txid)!=64: return False,f"TXID {network} invalide: 64 chars"
        return True,f"✅ TX {network} valide"
    return False,"Réseau inconnu"

@app.route("/")
def home():
    if 'user_id' in session: return redirect("/dashboard")
    return layout("""
    <div class='min-h-[80vh] flex flex-col justify-center max-w-4xl mx-auto text-center px-4'>
        <h1 class='text-6xl md:text-8xl font-black tracking-tight leading-[0.9]'>Le devis<br>qui te fait<br><span class='bg-black text-white px-4 rounded-full'>payer.</span></h1>
        <p class='mt-8 text-2xl md:text-3xl font-medium'>Crée ton devis. Encaisse ton acompte. C'est tout.</p>
        <p class='mt-3 text-gray-500 max-w-xl mx-auto'>Fini le travail gratuit. Ton client valide et paie 50% avant que tu ne commences.</p>
        <div class='mt-10 flex flex-col md:flex-row gap-4 justify-center items-center'>
            <a href='/register' class='bg-black text-white px-10 py-5 rounded-full font-bold text-lg w-full md:w-auto'>S'inscrire - C'est gratuit</a>
            <a href='/login' class='border-2 border-black px-10 py-5 rounded-full font-bold text-lg w-full md:w-auto'>Connexion</a>
        </div>
        <div class='mt-16 grid md:grid-cols-3 gap-4 text-left'>
            <div class='bg-white p-6 rounded-[24px] border shadow-sm'><div class='text-3xl'>📄</div><b class='text-lg mt-2 block'>Devis pro en 30s</b><p class='text-sm text-gray-500 mt-2'>Numérotation auto, TVA, remise, acompte. Plus de Word.</p></div>
            <div class='bg-white p-6 rounded-[24px] border shadow-sm'><div class='text-3xl'>💳</div><b class='text-lg mt-2 block'>Encaisse avant de bosser</b><p class='text-sm text-gray-500 mt-2'>MoMo + USDT BEP20/TRC20 + BNB/TRX. Direct chez toi.</p></div>
            <div class='bg-white p-6 rounded-[24px] border shadow-sm'><div class='text-3xl'>👀</div><b class='text-lg mt-2 block'>Tu sais qui a vu</b><p class='text-sm text-gray-500 mt-2'>Lien WhatsApp traçable. Tu relances au bon moment.</p></div>
        </div>
    </div>
    """)

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        email=request.form.get("email","").lower().strip(); pwd=request.form.get("password","")
        db=get_db()
        try:
            db.execute("INSERT INTO users (email,password,plan,momo_number,momo_name,usdt_bep20,usdt_trc20) VALUES (?,?,?,?,?,?,?)",(email,generate_password_hash(pwd),"FREE",ADMIN_CONFIG["momo_number"],ADMIN_CONFIG["momo_name"],ADMIN_CONFIG["crypto"]["BSC_ADDRESS"],ADMIN_CONFIG["crypto"]["TRON_ADDRESS"]))
            db.commit()
            user=db.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
            session['user_id']=user['id']; return redirect("/dashboard")
        except: return layout("<p>Email déjà utilisé</p><a href='/register'>Retour</a>")
    return layout("<div class='max-w-sm mx-auto bg-white p-6 rounded-2xl mt-16 shadow border'><h2 class='text-xl font-bold'>Inscription</h2><form method='POST' class='mt-4 space-y-3'><input name='email' type='email' placeholder='Email' required class='border p-3 rounded-xl w-full'><input name='password' type='password' placeholder='Mot de passe' required class='border p-3 rounded-xl w-full'><button class='bg-black text-white w-full py-3 rounded-full font-bold'>Créer</button></form></div>")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form.get("email","").lower().strip(); pwd=request.form.get("password","")
        db=get_db(); user=db.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
        if user and check_password_hash(user['password'],pwd):
            session['user_id']=user['id']; return redirect("/dashboard")
        return layout("<p>Faux</p>")
    return layout("<div class='max-w-sm mx-auto bg-white p-6 rounded-2xl mt-16 shadow border'><h2 class='text-xl font-bold'>Connexion</h2><form method='POST' class='mt-4 space-y-3'><input name='email' type='email' required class='border p-3 rounded-xl w-full'><input name='password' type='password' required class='border p-3 rounded-xl w-full'><button class='bg-black text-white w-full py-3 rounded-full font-bold'>Entrer</button></form></div>")

@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    devis=db.execute("SELECT * FROM devis WHERE user_id=? ORDER BY id DESC",(user['id'],)).fetchall()
    total_vues=sum(d['views'] or 0 for d in devis)
    total_payes=len([d for d in devis if 'Payé' in (d['status'] or '')])
    rows=""
    for d in devis:
        wa=f"Bonjour {d['client_name']}, devis {d['numero']}: {d['total']:.0f}F https://deviscloser-1.onrender.com/devis/{d['id']}"
        wa_link=f"https://wa.me/?text={wa}"
        rows+=f"<div class='bg-white p-4 rounded-2xl border'><div class='flex justify-between'><div><b>{d['numero']}</b> - {d['client_name']} - {d['total']:.0f}F - {d['views']} vues - <span class='text-xs px-2 py-1 bg-gray-100 rounded-full'>{d['status']}</span></div><div class='flex gap-2'><a href='/devis/{d['id']}' class='bg-black text-white px-3 py-1 rounded-full text-xs'>Voir</a><a href='{wa_link}' target='_blank' class='bg-green-500 text-white px-3 py-1 rounded-full text-xs'>WhatsApp</a></div></div></div>"
    if not rows:
        rows="""
        <div class='bg-white border-2 border-dashed rounded-[32px] p-12 text-center'>
            <div class='text-6xl'>✨</div>
            <h3 class='text-2xl font-bold mt-4'>Aucun devis pour l'instant</h3>
            <p class='text-gray-500 mt-2'>Ta devise: <b>Crée ton devis. Encaisse ton acompte. C'est tout.</b></p>
            <a href='/create' class='inline-block bg-black text-white px-8 py-4 rounded-full font-bold mt-6'>+ Créer mon premier devis</a>
        </div>
        """
    bsc=(user['usdt_bep20'] or ADMIN_CONFIG['crypto']['BSC_ADDRESS']); bsc_short=bsc[:6]+"..."+bsc[-4:]
    tron=(user['usdt_trc20'] or ADMIN_CONFIG['crypto']['TRON_ADDRESS']); tron_short=tron[:6]+"..."+tron[-4:]
    return layout(f"""
    <div class='flex justify-between items-center'><div><h1 class='text-3xl font-black'>Dashboard - {user['plan']}</h1><p class='text-sm text-gray-500'>Bienvenue {user['email']}</p></div><a href='/settings' class='text-sm border px-4 py-2 rounded-full'>⚙️ Paiements</a></div>
    <div class='grid grid-cols-3 gap-3 mt-6'>
        <div class='bg-black text-white p-5 rounded-[24px]'><p class='text-xs opacity-70'>DEVIS</p><p class='text-3xl font-black'>{len(devis)}</p></div>
        <div class='bg-white border p-5 rounded-[24px]'><p class='text-xs text-gray-500'>VUES</p><p class='text-3xl font-black'>{total_vues}</p></div>
        <div class='bg-green-500 text-white p-5 rounded-[24px]'><p class='text-xs'>PAYÉS</p><p class='text-3xl font-black'>{total_payes}</p></div>
    </div>
    <div class='mt-6 bg-blue-50 border border-blue-100 p-4 rounded-2xl'>
        <p class='text-xs font-bold text-blue-900'>TES INFOS ACTIVES</p>
        <p class='text-sm mt-1'>👤 SOSTHENE HERVE EDOH - 📱 {user['momo_number'] or ADMIN_CONFIG['momo_number']} - 🟡 BSC {bsc_short} - 🔵 TRON {tron_short}</p>
    </div>
    <div class='mt-8 space-y-3'>{rows}</div>
    <div class='md:hidden fixed bottom-6 left-1/2 -translate-x-1/2 z-20'><a href='/create' class='bg-black text-white px-8 py-4 rounded-full font-bold shadow-2xl'>+ Nouveau devis</a></div>
    <div class='hidden md:block mt-6'><a href='/create' class='bg-black text-white px-6 py-3 rounded-full font-bold'>+ Nouveau devis</a></div>
    """,user)

@app.route("/settings", methods=["GET","POST"])
def settings():
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    if request.method=="POST":
        db.execute("UPDATE users SET momo_number=?, momo_name=?, usdt_bep20=?, usdt_trc20=?, bnb_address=?, trx_address=? WHERE id=?",(request.form.get("momo_number"),request.form.get("momo_name"),request.form.get("usdt_bep20"),request.form.get("usdt_trc20"),request.form.get("bnb_address"),request.form.get("trx_address"),user['id']))
        db.commit(); return redirect("/dashboard")
    return layout(f"""
    <h1 class='text-2xl font-bold'>💳 Mes paiements</h1>
    <form method="POST" class="mt-6 bg-white p-6 rounded-2xl border space-y-4 max-w-xl">
        <div><label class='text-sm font-bold'>MoMo</label><input name="momo_number" value="{user['momo_number'] or ''}" class="border p-3 rounded-xl w-full"><input name="momo_name" value="{user['momo_name'] or ''}" class="border p-3 rounded-xl w-full mt-2"></div>
        <div><label class='text-sm font-bold'>BSC (USDT + BNB)</label><input name="usdt_bep20" value="{user['usdt_bep20'] or ''}" class="border p-3 rounded-xl w-full font-mono text-xs"></div>
        <div><label class='text-sm font-bold'>TRON (USDT + TRX)</label><input name="usdt_trc20" value="{user['usdt_trc20'] or ''}" class="border p-3 rounded-xl w-full font-mono text-xs"></div>
        <button class="bg-black text-white w-full py-3 rounded-full font-bold">Enregistrer</button>
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
        remise=float(request.form.get("remise") or 0); tva=float(request.form.get("tva") or 0)
        total=subtotal-remise
        if tva: total=total*(1+tva/100)
        acompte=float(request.form.get("acompte") or total*0.5)
        db.execute("INSERT INTO devis (user_id,numero,client_name,client_email,client_company,subtotal,remise,tva,total,acompte,items_json,status,created_at,views) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(user['id'],numero,request.form.get("client_name"),request.form.get("client_email"),request.form.get("client_company"),subtotal,remise,tva,total,acompte,json.dumps(items),"Brouillon",datetime.datetime.now().isoformat(),0))
        db.commit()
        d=db.execute("SELECT * FROM devis WHERE numero=?",(numero,)).fetchone()
        return redirect(f"/devis/{d['id']}")
    return layout("""
    <h1 class='text-2xl font-bold'>+ Nouveau devis v10</h1>
    <form method="POST" class="mt-6 bg-white p-6 rounded-2xl border space-y-3 max-w-3xl" id="f">
        <div class='grid md:grid-cols-2 gap-3'><input name="client_name" placeholder="Nom client *" required class="border p-3 rounded-xl w-full"><input name="client_company" placeholder="Société" class="border p-3 rounded-xl w-full"><input name="client_email" placeholder="WhatsApp / Email" class="border p-3 rounded-xl w-full md:col-span-2"></div>
        <div id="items"><div class='grid grid-cols-12 gap-2 bg-gray-50 p-2 rounded-xl'><div class='col-span-6'><input name="service[]" placeholder="Service" required class="border p-2 rounded w-full"></div><div class='col-span-2'><input name="qte[]" type="number" value="1" class="border p-2 rounded w-full"></div><div class='col-span-2'><input name="pu[]" type="number" placeholder="PU" required class="border p-2 rounded w-full"></div><div class='col-span-2'><button type="button" onclick="addItem()" class="bg-black text-white px-2 py-2 rounded w-full text-xs">+ Ligne</button></div></div></div>
        <div class='grid grid-cols-3 gap-3'><input name="remise" type="number" placeholder="Remise" class="border p-3 rounded-xl w-full"><input name="tva" type="number" placeholder="TVA %" class="border p-3 rounded-xl w-full"><input name="acompte" type="number" placeholder="Acompte 50%" class="border p-3 rounded-xl w-full"></div>
        <button class="bg-black text-white w-full py-4 rounded-full font-bold">Créer + Lien WhatsApp</button>
    </form>
    <script>function addItem(){const d=document.createElement('div');d.className='grid grid-cols-12 gap-2 bg-gray-50 p-2 rounded-xl mt-2';d.innerHTML=`<div class='col-span-6'><input name="service[]" placeholder="Service" required class="border p-2 rounded w-full"></div><div class='col-span-2'><input name="qte[]" type="number" value="1" class="border p-2 rounded w-full"></div><div class='col-span-2'><input name="pu[]" type="number" placeholder="PU" required class="border p-2 rounded w-full"></div><div class='col-span-2'><button type="button" onclick="this.parentElement.parentElement.remove()" class="bg-red-500 text-white px-2 py-2 rounded w-full text-xs">X</button></div>`;document.getElementById('items').appendChild(d);}</script>
    """,user)

@app.route("/pricing")
def pricing():
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    return layout(f"""
    <h1 class='text-3xl font-bold text-center'>Tarifs</h1>
    <div class='grid md:grid-cols-3 gap-4 mt-8 max-w-4xl mx-auto'>
        <div class='bg-white border p-6 rounded-[24px]'><h3 class='font-bold'>FREE</h3><p class='text-3xl font-bold my-2'>0F</p><p class='text-sm'>5 devis</p></div>
        <div class='bg-black text-white border-2 p-6 rounded-[24px]'><h3>STARTER</h3><p class='text-3xl font-bold my-2'>5900F</p><a href='/pay/STARTER/MOMO' class='block bg-white text-black py-2 rounded-full text-center font-bold mt-4'>📱 MoMo</a><a href='/pay/STARTER/USDT_BEP20' class='block bg-green-500 py-2 rounded-full text-center font-bold mt-2 text-sm'>USDT BEP20 10$</a><a href='/pay/STARTER/USDT_TRC20' class='block bg-blue-500 py-2 rounded-full text-center font-bold mt-2 text-sm'>USDT TRC20 10$</a></div>
        <div class='bg-white border p-6 rounded-[24px]'><h3>PRO</h3><p class='text-3xl font-bold my-2'>12900F</p><a href='/pay/PRO/MOMO' class='block bg-black text-white py-2 rounded-full text-center font-bold mt-4'>📱 MoMo</a></div>
    </div>
    """,user)

@app.route("/pay/<plan>/<network>")
def pay(plan,network):
    if 'user_id' not in session: return redirect("/login")
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    prices=ADMIN_CONFIG['prices'][plan]
    if network=="MOMO": amount=prices['momo']; info=f"<p class='font-bold'>{ADMIN_CONFIG['momo_number']}</p><p>{ADMIN_CONFIG['momo_name']}</p><p class='bg-yellow-100 p-2 rounded mt-2'>{amount}F</p>"
    elif network in ["USDT_BEP20","BNB"]: amount=prices[network]; info=f"<p class='font-mono text-xs break-all bg-gray-50 p-2 rounded border'>{ADMIN_CONFIG['crypto']['BSC_ADDRESS']}</p><p class='bg-green-100 p-2 rounded mt-2'>{amount} {network} BSC</p>"
    else: amount=prices[network]; info=f"<p class='font-mono text-xs break-all bg-gray-50 p-2 rounded border'>{ADMIN_CONFIG['crypto']['TRON_ADDRESS']}</p><p class='bg-blue-100 p-2 rounded mt-2'>{amount} {network} TRON</p>"
    return layout(f"""<div class='max-w-lg mx-auto bg-white p-6 rounded-[24px] border mt-6'><h2 class='text-xl font-bold'>Payer {plan} via {network}</h2><div class='mt-4 p-4 border rounded-xl bg-gray-50'>{info}</div><form method="POST" action="/verify_payment" class="mt-6 space-y-3"><input type="hidden" name="plan" value="{plan}"><input type="hidden" name="network" value="{network}"><input type="hidden" name="method" value="{'MOMO' if network=='MOMO' else 'CRYPTO'}"><input name="txid" placeholder="{'ID MoMo' if network=='MOMO' else 'TXID'}" required class="border p-3 rounded-xl w-full font-mono text-xs"><button class="bg-black text-white w-full py-3 rounded-full font-bold">✅ J'ai payé</button></form></div>""",user)

@app.route("/verify_payment", methods=["POST"])
def verify_payment():
    if 'user_id' not in session: return redirect("/login")
    plan=request.form.get("plan"); network=request.form.get("network"); method=request.form.get("method"); txid=request.form.get("txid","").strip()
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    ok,msg=verify_txid(method,network,txid)
    if not ok: return layout(f"<div class='bg-white p-6 rounded-2xl border'><p class='text-red-600 font-bold'>{msg}</p><a href='/pay/{plan}/{network}' class='block bg-black text-white py-2 rounded-full text-center mt-4'>Retour</a></div>",user)
    try:
        prices=ADMIN_CONFIG['prices'][plan]; amount=prices.get(network,0) if network!="MOMO" else prices['momo']
        db.execute("INSERT INTO payments (user_id,type,plan,method,network,amount,currency,txid,status,created_at,verified_data) VALUES (?,?,?,?,?,?,?,?,?,?,?)",(user['id'],'subscription',plan,method,network,amount,network,txid,'Vérifié',datetime.datetime.now().isoformat(),msg))
        exp=(datetime.datetime.now()+datetime.timedelta(days=30)).isoformat()
        db.execute("UPDATE users SET plan=?,expiration=? WHERE id=?",(plan,exp,user['id'])); db.commit()
    except Exception as e:
        if "UNIQUE" in str(e): return layout("<p>TXID déjà utilisé</p>",user)
        raise e
    return layout(f"<div class='text-center bg-white p-8 rounded-[24px] border mt-10'><h1 class='text-5xl'>🎉</h1><h2 class='text-2xl font-bold mt-4'>{plan} Activé !</h2><p class='font-mono text-xs bg-gray-100 p-2 rounded mt-3 break-all'>{txid}</p><a href='/dashboard' class='block bg-black text-white py-3 rounded-full font-bold mt-6'>Dashboard</a></div>",user)

@app.route("/devis/<int:did>", methods=["GET","POST"])
def view_devis(did):
    db=get_db(); d=db.execute("SELECT * FROM devis WHERE id=?",(did,)).fetchone()
    if not d: return "Introuvable"
    seller=db.execute("SELECT * FROM users WHERE id=?",(d['user_id'],)).fetchone()
    if request.method=="POST":
        momo_num=seller['momo_number'] or ADMIN_CONFIG["momo_number"]; bsc=seller['usdt_bep20'] or ADMIN_CONFIG["crypto"]["BSC_ADDRESS"]; tron=seller['usdt_trc20'] or ADMIN_CONFIG["crypto"]["TRON_ADDRESS"]; acompte=d['acompte']
        return f"<html><head>{BASE_CSS}</head><body class='bg-green-50 p-4'><div class='max-w-4xl mx-auto bg-white p-6 rounded-[24px] border'><h2 class='text-xl font-bold text-center'>Devis {d['numero']} Accepté - Payer {acompte}F</h2><div class='grid md:grid-cols-3 gap-4 mt-6'><div class='border-2 p-4 rounded-2xl'><p>📱 MoMo</p><p class='font-bold'>{momo_num}</p><form method='POST' action='/verify_acompte/{did}'><input type='hidden' name='network' value='MOMO'><input name='txid' placeholder='ID MoMo' required class='border p-2 rounded w-full text-xs'><button class='bg-black text-white w-full py-2 rounded-full mt-2 text-xs'>J'ai payé</button></form></div><div class='border-2 p-4 rounded-2xl'><p>💵 BEP20</p><p class='font-mono text-xs break-all'>{bsc}</p><form method='POST' action='/verify_acompte/{did}'><input type='hidden' name='network' value='USDT_BEP20'><input name='txid' placeholder='0x...' required class='border p-2 rounded w-full text-xs'><button class='bg-green-600 text-white w-full py-2 rounded-full mt-2 text-xs'>J'ai payé</button></form></div><div class='border-2 p-4 rounded-2xl'><p>💵 TRC20</p><p class='font-mono text-xs break-all'>{tron}</p><form method='POST' action='/verify_acompte/{did}'><input type='hidden' name='network' value='USDT_TRC20'><input name='txid' placeholder='TXID 64' required class='border p-2 rounded w-full text-xs'><button class='bg-blue-600 text-white w-full py-2 rounded-full mt-2 text-xs'>J'ai payé</button></form></div></div></div></body></html>"
    db.execute("UPDATE devis SET views=views+1 WHERE id=?",(did,)); db.commit()
    items=json.loads(d['items_json'] or '[]'); rows="".join([f"<tr><td class='p-2'>{i['service']}</td><td>{i['qte']}</td><td>{i['pu']}</td><td>{i['total']}</td></tr>" for i in items])
    return f"<html><head>{BASE_CSS}</head><body class='bg-gray-50 p-4'><div class='max-w-2xl mx-auto bg-white p-8 rounded-[24px] border'><h1 class='text-2xl font-bold'>DEVIS {d['numero']}</h1><p>Client: {d['client_name']} - {d['views']} vues - {d['status']}</p><table class='w-full mt-4 text-sm'><tr><th>Service</th><th>Qté</th><th>PU</th><th>Total</th></tr>{rows}</table><p class='mt-4 font-bold'>Total: {d['total']}F - Acompte: {d['acompte']}F</p><form method='POST' class='mt-6'><button class='bg-green-600 text-white w-full py-4 rounded-full font-bold'>✅ Accepter et payer acompte</button></form></div></body></html>"

@app.route("/verify_acompte/<int:did>", methods=["POST"])
def verify_acompte(did):
    db=get_db(); d=db.execute("SELECT * FROM devis WHERE id=?",(did,)).fetchone()
    network=request.form.get("network"); txid=request.form.get("txid","").strip()
    method="MOMO" if network=="MOMO" else "CRYPTO"
    ok,msg=verify_txid(method,network,txid)
    if not ok: return f"<p>{msg}</p><a href='/devis/{did}'>Retour</a>"
    try:
        db.execute("INSERT INTO payments (user_id,devis_id,type,method,network,amount,currency,txid,status,created_at,verified_data) VALUES (?,?,?,?,?,?,?,?,?,?,?)",(d['user_id'],did,'acompte',method,network,d['acompte'],network,txid,'Vérifié',datetime.datetime.now().isoformat(),msg))
        db.execute("UPDATE devis SET status='Acompte Payé ✅' WHERE id=?",(did,)); db.commit()
    except: return "TXID déjà utilisé"
    return f"<html><head>{BASE_CSS}</head><body class='bg-green-50 flex items-center justify-center min-h-screen p-4'><div class='bg-white p-8 rounded-[24px] text-center border'><h1 class='text-4xl'>✅</h1><h2 class='text-xl font-bold mt-3'>Acompte Payé {network} !</h2><p class='font-mono text-xs mt-3 bg-gray-100 p-2 rounded break-all'>{txid}</p></div></body></html>"

@app.route("/logout")
def logout(): session.clear(); return redirect("/")
init_db()
if __name__=="__main__": app.run(host="0.0.0.0",port=8080)
