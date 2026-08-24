"""
Resolution helpers: bridges the NLP layer's NAME-based output
(customer_name="Raju", item="chairs") to the database's ID-based schema
(customer_id, item_id).

This is the actual "glue" between Monisha's NLU output and Kiruba's
existing booking/payment/return endpoints.
"""

import difflib
from sqlalchemy.orm import Session

from app.models.database_models import Customer, CustomerAlias, Inventory


# Explicit alias table: maps common spoken words (English, Kannada
# transliteration, or code-mixed) to a substring that should match the
# canonical inventory item_name. Checked BEFORE fuzzy matching, since
# fuzzy string similarity alone was producing low-confidence matches
# (e.g. "chairs" -> "Plastic Chair" at only 0.53) and completely missing
# valid domain words like "kaipatre" that aren't textually similar enough
# to "Pathre" for difflib to catch on its own.
#
# NOTE FOR THE TEAM: this list is a starting point built from the example
# sentences in the project proposal/abstract - it should grow as real
# owner speech reveals more item name variants. Whoever owns inventory
# data (Kiruba) should review/extend this alongside seed.py.
ITEM_ALIASES = {
    "chair": "chair",
    "chairs": "chair",
    "cheeru": "chair",
    "plate": "plate",
    "plates": "plate",
    "pathre": "pathre",
    "vessel": "pathre",
    "vessels": "pathre",
    "kaipatre": "pathre",   # hand-vessel - treated as the general vessel/pathre category
    "kaipathre": "pathre",
    "table": "table",
    "tables": "table",
    "tent": "tent",
    "canopy": "tent",
    "mat": "mat",
    "mats": "mat",
    "light": "light",
    "lights": "light",
}


def find_or_create_customer(db: Session, name: str, phone: str = None) -> Customer:
    """
    Looks up a customer by name (case-insensitive), then by confirmed
    alias, and only creates a new customer if neither matches.

    Per team decision: aliases are NEVER auto-detected or auto-merged here.
    They only exist in the alias table after the owner has explicitly
    confirmed "yes, same person" via voice (see /customers/similar and
    /customers/{id}/aliases in routes/customers.py) - this function just
    reads whatever's already been confirmed, it doesn't do any fuzzy
    guessing itself.
    """
    existing = (
        db.query(Customer)
        .filter(Customer.name.ilike(name.strip()))
        .first()
    )
    if existing:
        return existing

    alias_match = (
        db.query(CustomerAlias)
        .filter(CustomerAlias.alias_name.ilike(name.strip()))
        .first()
    )
    if alias_match:
        return db.query(Customer).filter(Customer.customer_id == alias_match.customer_id).first()

    new_customer = Customer(name=name.strip(), phone=phone, address=None)
    db.add(new_customer)
    db.flush()  # get the new customer_id without committing yet
    return new_customer


def suggest_similar_customers(db: Session, name: str, cutoff: float = 0.6):
    """
    Returns a list of existing customers whose names are similar to the
    given name, WITHOUT merging anything automatically. Intended for a
    human (owner/admin) to review and confirm "yes this is the same
    person" via voice (see /customers/similar in routes/customers.py).

    DOCUMENTED LIMITATION (tested Aug 2026, not fixed - see project report):
    This uses plain character-level string similarity (difflib), which
    only catches name variants that share overlapping SUBSTRINGS - e.g.
    "Raju" vs "Raju anna" scores high since one is literally contained in
    the other. It does NOT catch real Indian nickname patterns like
    "Rajashekar" -> "Raju" (measured similarity: 0.43, well below the 0.6
    cutoff), even though any Kannada speaker would immediately recognize
    "Raju" as a common nickname derived from "Rajashekar".

    This is a genuine, known limitation of edit-distance-based matching
    for nickname resolution - it doesn't encode cultural/linguistic
    knowledge about how nicknames are actually formed. A more complete
    solution would need either:
      (a) a curated common-name-variant dictionary (Raja*->Raju,
          Krishna->Krishna anna, etc.), or
      (b) phonetic matching (Soundex/Metaphone-style algorithms)
    Lowering the cutoff was considered and rejected - it trades this
    false-negative problem for false positives (unrelated names getting
    incorrectly flagged as possible matches), which is a worse failure
    mode for a system handling real customer data and money.
    """
    all_customers = db.query(Customer).all()
    matches = []
    for cust in all_customers:
        score = difflib.SequenceMatcher(None, name.lower(), cust.name.lower()).ratio()
        if score >= cutoff and cust.name.lower() != name.lower():
            matches.append((cust, score))
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches


def resolve_item_id(db: Session, item_name: str, cutoff: float = 0.5):
    """
    Resolves an NLU item string (e.g. "chair", "pathre", "kaipatre")
    against the Inventory table. Returns (Inventory row, match_score) or
    (None, 0) if nothing matches well enough.

    Matching order:
    1. Alias table (ITEM_ALIASES above) - explicit, deterministic, highest
       confidence for known domain vocabulary.
    2. Exact substring match against inventory item_name.
    3. Fuzzy string similarity as a last resort.
    """
    if not item_name:
        return None, 0.0

    all_items = db.query(Inventory).all()
    if not all_items:
        return None, 0.0

    item_name_lower = item_name.strip().lower()

    # 1. Alias table lookup
    canonical = ITEM_ALIASES.get(item_name_lower)
    if canonical:
        for inv in all_items:
            if canonical in inv.item_name.lower():
                return inv, 1.0

    # 2. Exact substring match (e.g. "chair" in "plastic chair")
    for inv in all_items:
        if item_name_lower in inv.item_name.lower():
            return inv, 1.0

    # 3. Fuzzy string matching, case-insensitive on both sides
    names_lower_map = {inv.item_name.lower(): inv for inv in all_items}
    close = difflib.get_close_matches(item_name_lower, list(names_lower_map.keys()), n=1, cutoff=cutoff)
    if close:
        matched_inv = names_lower_map[close[0]]
        score = difflib.SequenceMatcher(None, item_name_lower, close[0]).ratio()
        return matched_inv, score

    return None, 0.0