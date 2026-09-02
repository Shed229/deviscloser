# -*- coding: utf-8 -*-
"""
DevisCloser - v19.1 FINAL
CRITICAL FIX: Correct SLOGAN now applied.
"""
__version__ = "19.1-FINAL"

# ------------------------------
# CONFIGURATION
# ------------------------------
SLOGAN = "Devis Closer — Faites de vos devis des contrats."
MOMO_NUMBER = "2290156853149"   # MOMO pay service number (country code +229)
MOMO_DISPLAY = "01 56 85 31 49" # Display format for users
COUNTRY_CODE = "+229"
COUNTRY = "Bénin"

# Pricing - in XOF
STARTER_PRICE = 6500
PRO_PRICE = 15000

# SEO meta
SEO_TITLE = "DevisCloser — Devis → Contrats en quelques clics | Bénin +229"
SEO_DESCRIPTION = "Transformez vos devis en contrats signés. Paiement Mobile Money MOMO sécurisé. Devis, abonnement, facturation pour entrepreneurs au Bénin."
SEO_KEYWORDS = "devis, contrat, deviscloser, bénin, momo, mobile money, facture, abonnement, devis en contrat, +229"

# App behavior
IS_OWNER = True
DELIVERY_DATE = "2025-11-15"  # Target delivery date for service

# ------------------------------
# ANTI-BLACK-PAGE FIX
# ------------------------------
DEFAULT_CSS = """
body { margin:0; padding:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; background:#f6fdf8; color:#0f172a; }
.container { max-width: 960px; margin: 0 auto; padding: 24px; }
.header { background: #0a7a3f; color: #fff; padding: 16px 24px; border-radius: 12px; }
.card { background: #ffffff; border: 1px solid #d1fae5; border-radius: 12px; padding: 20px; margin: 16px 0; box-shadow: 0 2px 8px rgba(10,122,63,0.08); }
.btn { display:inline-block; padding:10px 16px; background:#10b981; color:#fff; text-decoration:none; border-radius:8px; font-weight:600; }
.btn:hover { background:#059669; }
.price { font-size: 1.8rem; font-weight:700; color:#065f46; }
.footer { font-size:0.85rem; color:#475569; margin-top:32px; border-top:1px solid #e2e8f0; padding-top:16px; }
.cgu { font-size:0.8rem; color:#334155; background:#ecfdf5; padding:12px; border-radius:8px; border:1px solid #a7f3d0; }
.badge { background:#d1fae5; color:#065f46; padding:4px 8px; border-radius:9999px; font-size:0.75rem; font-weight:600; }
"""

ROUTES = {
    "/": "home",
    "/pricing": "pricing",
    "/subscribe": "subscribe",
    "/pay": "pay",
    "/momo": "momo",
    "/devis": "devis",
    "/cgu": "cgu",
}

def render_home():
    return f"<!doctype html>\n<html lang='fr'>\n<head>\n<meta charset='utf-8'>\n<meta name='viewport' content='width=device-width, initial-scale=1'>\n<title>{SEO_TITLE}</title>\n<meta name='description' content='{SEO_DESCRIPTION}'>\n<meta name='keywords' content='{SEO_KEYWORDS}'>\n<style>{DEFAULT_CSS}</style>\n</head>\n<body>\n<div class='container'>\n  <div class='header'>\n    <h1>DevisCloser <span class='badge'>v{__version__}</span></h1>\n    <p>{SLOGAN}</p>\n    <small>{COUNTRY} — {COUNTRY_CODE}</small>\n  </div>\n  <div class='card'>\n    <h2>Bienvenue sur DevisCloser</h2>\n    <p>Transformez vos devis en contrats signés, simplement et rapidement.</p>\n    <p><a class='btn' href='/pricing'>Voir les offres</a> <a class='btn' style='background:#047857' href='/devis'>Créer un devis</a></p>\n  </div>\n  <div class='card'>\n    <h3>Fonctionnalités</h3>\n    <ul>\n      <li>Création et suivi de devis → contrat</li>\n      <li>Paiement Mobile Money MOMO intégré</li>\n      <li>Abonnement Starter & Pro</li>\n      <li>Livraison prévue: <strong>{DELIVERY_DATE}</strong></li>\n    </ul>\n  </div>\n  <div class='footer'>\n    <p>Propriétaire: {'Actif' if IS_OWNER else 'Client'} | Contact MOMO: {MOMO_DISPLAY} ({MOMO_NUMBER})</p>\n    <p><a href='/cgu'>Conditions Générales d'Utilisation (CGU)</a> | <a href='/pricing'>Tarifs</a></p>\n  </div>\n</div>\n</body>\n</html>\n"

def render_pricing():
    return f"<!doctype html>\n<html lang='fr'>\n<head>\n<meta charset='utf-8'>\n<title>Tarifs - DevisCloser</title>\n<meta name='description' content='Abonnements DevisCloser: Starter 6500 XOF, Pro 15000 XOF. Paiement MOMO {COUNTRY_CODE}'>\n<meta name='keywords' content='{SEO_KEYWORDS}, tarifs, abonnement'>\n<style>{DEFAULT_CSS}</style>\n</head>\n<body>\n<div class='container'>\n  <div class='header'>\n    <h1>Nos Forfaits</h1>\n    <p>{SLOGAN}</p>\n  </div>\n  <div class='card'>\n    <h2>Starter</h2>\n    <p class='price'>{STARTER_PRICE} XOF / mois</p>\n    <ul>\n      <li>10 devis / mois</li>\n      <li>Paiement MOMO</li>\n      <li>Support Email</li>\n    </ul>\n    <p><a class='btn' href='/subscribe?plan=starter'>S'abonner Starter</a></p>\n  </div>\n  <div class='card'>\n    <h2>Pro</h2>\n    <p class='price'>{PRO_PRICE} XOF / mois</p>\n    <ul>\n      <li>Devis illimités</li>\n      <li>Contrats automatiques</li>\n      <li>Support Prioritaire MOMO</li>\n      <li>Export PDF & contrat signé</li>\n    </ul>\n    <p><a class='btn' href='/subscribe?plan=pro'>S'abonner Pro</a></p>\n  </div>\n  <div class='footer'><a href='/'>← Retour Accueil</a></div>\n</div>\n</body>\n</html>\n"

def render_subscribe(plan=None):
    plan = plan or "starter"
    price = STARTER_PRICE if plan == "starter" else PRO_PRICE
    return f"<!doctype html>\n<html lang='fr'>\n<head>\n<meta charset='utf-8'>\n<title>S'abonner - {plan.upper()}</title>\n<meta name='description' content='Souscription {plan} - {price} XOF - Paiement MOMO {MOMO_DISPLAY}'>\n<style>{DEFAULT_CSS}</style>\n</head>\n<body>\n<div class='container'>\n  <div class='header'><h1>Abonnement {plan.upper()}</h1><p>{SLOGAN}</p></div>\n  <div class='card'>\n    <h2>Confirmer votre abonnement</h2>\n    <p>Plan: <strong>{plan.upper()}</strong></p>\n    <p>Montant: <span class='price'>{price} XOF / mois</span></p>\n    <p>Paiement via Mobile Money MOMO</p>\n    <p><a class='btn' href='/pay?plan={plan}&amount={price}'>Payer maintenant</a></p>\n  </div>\n  <div class='footer'><a href='/pricing'>← Retour Tarifs</a></div>\n</div>\n</body>\n</html>\n"

def render_pay(plan=None, amount=None):
    amount = amount or STARTER_PRICE
    plan = plan or "starter"
    return f"<!doctype html>\n<html lang='fr'>\n<head>\n<meta charset='utf-8'>\n<title>Paiement - DevisCloser</title>\n<style>{DEFAULT_CSS}</style>\n</head>\n<body>\n<div class='container'>\n  <div class='header'><h1>Paiement sécurisé</h1><p>{SLOGAN}</p></div>\n  <div class='card'>\n    <h2>Paiement via MOMO</h2>\n    <p>Plan: <strong>{plan.upper()}</strong></p>\n    <p>Montant à payer: <span class='price'>{amount} XOF</span></p>\n    <p>Envoyez le paiement au numéro MOMO:</p>\n    <div class='card' style='background:#ecfdf5; border:1px solid #10b981;'>\n      <p style='font-size:1.2rem; margin:8px 0;'><strong>MOMO: {MOMO_DISPLAY}</strong></p>\n      <p style='font-family: monospace;'>Numéro: {MOMO_NUMBER}</p>\n      <p>Référence: DEVISCLOSER-{plan.upper()}</p>\n    </div>\n    <p>Après paiement, votre abonnement sera activé automatiquement.</p>\n    <p><a class='btn' href='/momo?status=pending'>J'ai payé - Vérifier</a></p>\n  </div>\n  <div class='footer'><a href='/subscribe?plan={plan}'>← Retour</a></div>\n</div>\n</body>\n</html>\n"

def render_momo(status="pending"):
    return f"<!doctype html>\n<html lang='fr'>\n<head>\n<meta charset='utf-8'>\n<title>MOMO Paiement</title>\n<style>{DEFAULT_CSS}</style>\n</head>\n<body>\n<div class='container'>\n  <div class='header'><h1>Paiement MOMO</h1><p>{SLOGAN}</p></div>\n  <div class='card'>\n    <h2>Statut: {status.upper()}</h2>\n    <p>Suivez votre paiement Mobile Money.</p>\n    <p>Numéro MOMO: <strong>{MOMO_DISPLAY}</strong> ({MOMO_NUMBER})</p>\n    <p>Une fois le paiement confirmé, votre accès est activé.</p>\n    <p class='cgu'>Assurez-vous d'utiliser le même numéro pour la confirmation.</p>\n  </div>\n  <div class='footer'><a href='/'>← Accueil</a></div>\n</div>\n</body>\n</html>\n"

def render_devis():
    return f"<!doctype html>\n<html lang='fr'>\n<head>\n<meta charset='utf-8'>\n<title>Créer un Devis</title>\n<style>{DEFAULT_CSS}</style>\n</head>\n<body>\n<div class='container'>\n  <div class='header'><h1>Créer un Devis</h1><p>{SLOGAN}</p></div>\n  <div class='card'>\n    <h2>Nouveau Devis → Contrat</h2>\n    <form>\n      <p><label>Client: <input type='text' placeholder='Nom du client' style='padding:8px; width:100%; border:1px solid #cbd5e1; border-radius:6px;'></label></p>\n      <p><label>Montant: <input type='number' placeholder='Montant en XOF' style='padding:8px; width:100%; border:1px solid #cbd5e1; border-radius:6px;'></label></p>\n      <p><label>Description: <textarea placeholder='Description du service' rows='3' style='padding:8px; width:100%; border:1px solid #cbd5e1; border-radius:6px;'></textarea></label></p>\n      <p><a class='btn' onclick=\"alert('Devis créé! Prêt à être transformé en contrat.');\">Générer le Devis</a></p>\n    </form>\n  </div>\n  <div class='footer'><a href='/'>← Accueil</a></div>\n</div>\n</body>\n</html>\n"

def render_cgu():
    return f"<!doctype html>\n<html lang='fr'>\n<head>\n<meta charset='utf-8'>\n<title>CGU - DevisCloser</title>\n<style>{DEFAULT_CSS}</style>\n</head>\n<body>\n<div class='container'>\n  <div class='header'><h1>Conditions Générales d'Utilisation</h1><p>{SLOGAN}</p></div>\n  <div class='card cgu'>\n    <h2>CGU DevisCloser - v{__version__}</h2>\n    <p>En utilisant DevisCloser, vous acceptez les présentes conditions.</p>\n    <ul>\n      <li>Service destiné aux professionnels au {COUNTRY} ({COUNTRY_CODE})</li>\n      <li>Les paiements sont traités via Mobile Money MOMO au {MOMO_DISPLAY}</li>\n      <li>Abonnement: Starter {STARTER_PRICE} XOF, Pro {PRO_PRICE} XOF, renouvellement mensuel.</li>\n      <li>Données personnelles: conformes à la réglementation locale.</li>\n      <li>Livraison du service prévue pour: {DELIVERY_DATE}</li>\n    </ul>\n    <p>Contact: MOMO {MOMO_DISPLAY} | Support: support@deviscloser.bj</p>\n  </div>\n  <div class='footer'><a href='/'>← Accueil</a></div>\n</div>\n</body>\n</html>\n"

if __name__ == "__main__":
    print("DevisCloser v19.1 FINAL - Ready")
    print(f"SLOGAN: {SLOGAN}")
    print(f"MOMO: {MOMO_DISPLAY} / {MOMO_NUMBER}")
    print(f"Pricing: STARTER={STARTER_PRICE} XOF, PRO={PRO_PRICE} XOF")
    print(f"Country: {COUNTRY} {COUNTRY_CODE}")
    print(f"Delivery Date: {DELIVERY_DATE}")
    print(f"Routes available: {', '.join(ROUTES.keys())}")
    print("Anti-black-page: CSS fallback enabled.")
    print("SEO meta tags configured.")
