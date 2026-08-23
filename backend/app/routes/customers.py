from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.database_models import Customer


router = APIRouter(
    prefix="/customers",
    tags=["Customers"]
)


class CustomerCreate(BaseModel):
    name: str
    phone: str = None
    address: str = None


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
