from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.database_models import Customer, CustomerAlias
from app.services.matching import suggest_similar_customers


router = APIRouter(
    prefix="/customers",
    tags=["Customers"]
)


class CustomerCreate(BaseModel):
    name: str
    phone: str = None
    address: str = None


class AliasCreate(BaseModel):
    alias_name: str


@router.get("/")
def get_customers(
    db: Session = Depends(get_db)
):

    customers = db.query(Customer).all()

    return customers


@router.post("/")
def create_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db)
):

    customer = Customer(
        name=customer_data.name,
        phone=customer_data.phone,
        address=customer_data.address
    )

    db.add(customer)
    db.commit()
    db.refresh(customer)

    return customer


@router.get("/similar")
def check_similar_customers(
    name: str,
    db: Session = Depends(get_db)
):
    """
    Called by the NLP client BEFORE finalizing a transaction, to check if
    a spoken customer name might be an existing customer under a slightly
    different name/nickname. Per team decision: this only SUGGESTS matches
    - it never auto-merges. The owner must be asked and confirm via voice;
    if confirmed, the client calls POST /customers/{id}/aliases to record it.
    """
    matches = suggest_similar_customers(db, name)
    return [
        {"customer_id": cust.customer_id, "name": cust.name, "similarity": round(score, 2)}
        for cust, score in matches
    ]


@router.post("/{customer_id}/aliases")
def add_customer_alias(
    customer_id: int,
    alias_data: AliasCreate,
    db: Session = Depends(get_db)
):
    """
    Records a confirmed alias - only called AFTER the owner has verbally
    confirmed "yes, same person" for a suggested match from /similar.
    """
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        return {"error": "Customer not found"}

    alias = CustomerAlias(customer_id=customer_id, alias_name=alias_data.alias_name.strip())
    db.add(alias)
    db.commit()
    db.refresh(alias)

    return {"status": "success", "customer_id": customer_id, "alias_name": alias.alias_name}
