from pydantic import BaseModel, Field


class ReturnRequest(BaseModel):

    booking_id: int

    item_id: int

    quantity_returned: int = Field(gt=0)

    notes: str = ""