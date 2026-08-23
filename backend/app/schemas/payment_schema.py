from pydantic import BaseModel, Field


class PaymentRequest(BaseModel):

    booking_id: int

    amount: float = Field(gt=0)

    payment_method: str