from datetime import date
from pydantic import BaseModel, Field
from typing import List


class BookingItemRequest(BaseModel):
    item_id: int
    quantity: int = Field(gt=0)


class BookingRequest(BaseModel):
    customer_id: int
    event_date: date
    items: List[BookingItemRequest]