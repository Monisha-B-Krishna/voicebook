"""
Resolution helpers: bridges the NLP layer's NAME-based output
(customer_name="Raju", item="chairs") to the database's ID-based schema
(customer_id, item_id).

This is the actual "glue" between Monisha's NLU output and Kiruba's
existing booking/payment/return endpoints.
"""

import difflib
from sqlalchemy.orm import Session

from app.models.database_models import Customer, Inventory


def find_or_create_customer(db: Session, name: str, phone: str = None) -> Customer:
    """
    Looks up a customer by name (case-insensitive). If not found, creates
    a new one. This does NOT do fuzzy alias matching yet (e.g. "Raju" vs
    "Raju anna" vs "Rajashekar") - that's a known gap, see NOTES below.

    NOTES for the team:
    - The project's stated design goal is alias/nickname resolution
      (e.g. "Raju" / "Raju anna" / "Rajashekar" -> same customer). This
      function does simple exact-match-on-name for now. A real alias
      table (customer_id -> list of known aliases) would be the correct
      fix, but that's a schema change - flagging for a team decision
      rather than guessing at a fuzzy-match threshold that could
      silently merge two different real customers.
    """
    existing = (
        db.query(Customer)
        .filter(Customer.name.ilike(name.strip()))
        .first()
    )
    if existing:
        return existing

    new_customer = Customer(name=name.strip(), phone=phone, address=None)
    db.add(new_customer)
    db.flush()  # get the new customer_id without committing yet
    return new_customer


def resolve_item_id(db: Session, item_name: str, cutoff: float = 0.5):
    """
    Fuzzy-matches an NLU item string (e.g. "chair", "pathre", "kaipatre")
    against the Inventory table's item_name (e.g. "Plastic Chair",
    "Wedding Tent"). Returns (Inventory row, match_score) or (None, 0) if
    nothing matches well enough.

    KNOWN GAP: the seeded inventory (Plastic Chair, Round Table, Wedding
    Tent, LED Light, Plastic Mat) has NO vessel/pathre category at all,
    despite the project's own example sentences using "pathre" as a core
    example. "pathre" and "kaipatre" will currently resolve to nothing.
    This needs either: (a) adding a Vessels/Pathre category to seed.py,
    or (b) an explicit item alias/vocabulary table mapping spoken item
    words to inventory categories. Flagging this rather than silently
    matching "pathre" to something wrong like "Plastic Mat".
    """
    if not item_name:
        return None, 0.0

    all_items = db.query(Inventory).all()
    if not all_items:
        return None, 0.0

    item_name_lower = item_name.strip().lower()

    # 1. Try exact substring match first (e.g. "chair" in "plastic chair")
    for inv in all_items:
        if item_name_lower in inv.item_name.lower():
            return inv, 1.0

    # 2. Fall back to fuzzy string matching (case-insensitive, matching the
    # substring check above - comparing raw-case strings was under-matching
    # correct items just due to capitalization differences)
    names_lower_map = {inv.item_name.lower(): inv for inv in all_items}
    close = difflib.get_close_matches(item_name_lower, list(names_lower_map.keys()), n=1, cutoff=cutoff)
    if close:
        matched_inv = names_lower_map[close[0]]
        score = difflib.SequenceMatcher(None, item_name_lower, close[0]).ratio()
        return matched_inv, score

    return None, 0.0