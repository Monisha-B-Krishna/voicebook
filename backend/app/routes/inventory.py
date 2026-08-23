from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.database_models import Inventory


router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"]
)


@router.get("/")
def get_inventory(
    db: Session = Depends(get_db)
):

    inventory = db.query(Inventory).all()

    return inventory
    