"""
deviscloser_complet.py v18 FINAL
Devis Closer — Faites de vos devis des contrats.
"""
import datetime
from typing import Optional

# SLOGAN constant
SLOGAN = "Devis Closer — Faites de vos devis des contrats."

# SEO metadata
SEO = {
    "title": "Devis Closer — Faites de vos devis des contrats | Générez un devis professionnel",
    "meta_description": "Créez, envoyez et validez vos devis en quelques minutes. Transformez vos devis en contrats avec signature électronique, conditions générales et suivi livraison.",
    "keywords": "devis, contrat, freelance, facture, CGU, devis en ligne, signature électronique"
}

# Single FAQ
FAQ = [
    {
        "q": "Comment transformer mon devis en contrat ?",
        "a": "Une fois le devis accepté par le client et la case CGU cochée, le devis devient un contrat contraignant. Vous pouvez suivre la date de livraison et le statut."
    }
]

# Country codes select
COUNTRY_CODES = [
    ("FR", "France (+33)"),
    ("BE", "Belgique (+32)"),
    ("CH", "Suisse (+41)"),
    ("CA", "Canada (+1)"),
    ("MA", "Maroc (+212)"),
    ("TN", "Tunisie (+216)"),
    ("SN", "Sénégal (+221)"),
    ("CI", "Côte d'Ivoire (+225)"),
]

class Devis:
    def __init__(
        self,
        owner_id: str,
        client_id: str,
        project_title: str,
        amount_ht: float,
        delivery_date: str,  # YYYY-MM-DD
        country_code: str,
        cgu_accepted: bool = False,
    ):
        self.owner_id = owner_id
        self.client_id = client_id
        self.project_title = project_title
        self.amount_ht = amount_ht
        self.delivery_date = delivery_date
        self.country_code = country_code
        self.cgu_accepted = cgu_accepted
        self.status = "draft"
        self.created_at = datetime.date.today().isoformat()

    def is_owner(self, user_id: str) -> bool:
        """Return True if the given user_id is the owner of the devis."""
        return user_id == self.owner_id

    def is_client(self, user_id: str) -> bool:
        """Return True if the given user_id is the client of the devis."""
        return user_id == self.client_id

    def can_edit(self, user_id: str) -> bool:
        """Only owner can edit while in draft state."""
        return self.is_owner(user_id) and self.status == "draft"

    def accept_by_client(self, user_id: str) -> bool:
        """Client can accept if CGU is accepted."""
        if not self.is_client(user_id):
            return False
        if not self.cgu_accepted:
            raise ValueError("Les CGU doivent être acceptées avant d'accepter le devis.")
        self.status = "accepted"
        return True

# Example usage / helper functions
def render_hero():
    return {
        "slogan": SLOGAN,
        "sub": "Créez un devis, récupérez l'accord, sécurisez la livraison.",
    }

def render_form_fields():
    return {
        "project_title": {"label": "Titre du projet", "required": True},
        "amount_ht": {"label": "Montant HT (€)", "required": True, "type": "number"},
        "delivery_date": {"label": "Date de livraison prévue", "required": True, "type": "date"},
        "country_code": {"label": "Pays", "required": True, "type": "select", "options": COUNTRY_CODES},
        "cgu_checkbox": {"label": "J'accepte les Conditions Générales d'Utilisation (CGU)", "required": True, "type": "checkbox"},
    }

def render_faq():
    return FAQ[0]  # single faq

if __name__ == "__main__":
    print(SLOGAN)
    print("SEO Title:", SEO["title"])
    print("FAQ:", FAQ[0]["q"])
    # Example
    d = Devis(owner_id="u123", client_id="u456", project_title="Site web vitrine", amount_ht=1500.0,
              delivery_date="2026-11-30", country_code="FR", cgu_accepted=True)
    print("Is owner u123:", d.is_owner("u123"))
    print("Is client u456:", d.is_client("u456"))
    print("Can edit:", d.can_edit("u123"))
    print("Delivery date:", d.delivery_date)
    print("Country code:", d.country_code)
    print("Status:", d.status)
    d.accept_by_client("u456")
    print("Status after accept:", d.status)
