"""
NLUResult schema - validates the structured JSON that Claude returns
after parsing a transcribed (codemixed Kannada-English) utterance.

This is the contract between the NLU layer (your part) and the
Business Logic layer (Kiruba's part).
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class IntentType(str, Enum):
    BOOKING = "BOOKING"
    PAYMENT = "PAYMENT"
    RETURN = "RETURN"
    QUERY = "QUERY"
    UNKNOWN = "UNKNOWN"


class Transaction(BaseModel):
    """
    One structured transaction extracted from the utterance.
    A single utterance can produce MULTIPLE Transaction objects
    (this is how multi-intent utterances like
    'Raju ge June 15 ge 50 pathre booking maadidaare, 2000 advance kottidaare'
    get decomposed into a BOOKING + a PAYMENT).
    """

    intent: IntentType

    customer_name: Optional[str] = Field(
        default=None,
        description="Customer name/nickname as spoken, e.g. 'Raju', 'Raju anna'",
    )

    date: Optional[str] = Field(
        default=None,
        description="Explicit booking/event date, ONLY if stated in the utterance. "
        "ISO format YYYY-MM-DD. If not explicitly mentioned, leave null - "
        "the entry_timestamp is used as the default booking date downstream, "
        "not this field.",
    )

    item: Optional[str] = Field(
        default=None,
        description="Item/vessel type mentioned, e.g. 'pathre', 'chairs', 'canopy'",
    )

    quantity: Optional[int] = Field(
        default=None,
        description="Number of items booked/returned",
    )

    amount: Optional[float] = Field(
        default=None,
        description="Money amount mentioned (advance, payment, balance), in INR",
    )

    payment_type: Optional[str] = Field(
        default=None,
        description="'advance', 'balance', 'full' - only relevant for PAYMENT intent",
    )

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("quantity must be positive")
        return v

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v):
        if v is not None and v < 0:
            raise ValueError("amount cannot be negative")
        return v


class NLUResult(BaseModel):
    """
    Top-level output of the NLU layer for one utterance.
    Always a LIST of transactions, even if there's only one -
    this keeps single-intent and multi-intent utterances
    structurally identical for the Business Logic layer.
    """

    raw_transcript: str = Field(
        description="The original ASR transcript that was parsed"
    )

    entry_timestamp: str = Field(
        description="When this utterance was recorded/spoken (ISO 8601). Set by "
        "the system, not the NLU model. Used as the default booking date whenever "
        "a transaction's own 'date' field is null - i.e. 'the owner is logging "
        "this today, so assume today's date unless he said otherwise.'"
    )

    transactions: list[Transaction] = Field(
        default_factory=list,
        description="One or more structured transactions extracted from the utterance",
    )

    is_multi_intent: bool = Field(
        default=False,
        description="True if more than one transaction was detected in a single utterance",
    )

    confidence_note: Optional[str] = Field(
        default=None,
        description="Optional note if any field was ambiguous or guessed",
    )


# --- Quick manual test ---
if __name__ == "__main__":
    example = {
        "raw_transcript": "ರಾಜುಗೆ fifteen chairs ಕೊಟ್ಟಿದ್ದೀವಿ so fifteen enter ಮಾಡಿ",
        "entry_timestamp": "2026-08-10T21:45:00",
        "transactions": [
            {
                "intent": "BOOKING",
                "customer_name": "Raju",
                "item": "chairs",
                "quantity": 15,
            }
        ],
        "is_multi_intent": False,
    }

    result = NLUResult(**example)
    print(result.model_dump_json(indent=2))
