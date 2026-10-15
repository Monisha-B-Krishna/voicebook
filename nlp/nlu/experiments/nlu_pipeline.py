"""
NLU pipeline: takes a codemixed Kannada-English transcript (from Sarvam ASR)
and sends it to Claude to extract structured intent + entities.
Output is validated against NLUResult (see nlu_schema.py).

Run: python nlu_pipeline.py
"""

import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic
from pydantic import ValidationError

from nlu_schema import NLUResult

load_dotenv()  # reads ANTHROPIC_API_KEY from .env

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are the NLU layer for VoiceBook, a voice assistant for a \
Kannada-speaking tent house (event equipment rental) owner in Bengaluru.

You will receive a transcript of the owner's speech, in code-mixed Kannada-English \
(Kannada words in Kannada script, English words in Latin script).

Your job: extract one or more structured transactions from the utterance.

Each transaction has:
- intent: one of BOOKING, PAYMENT, RETURN, QUERY, UNKNOWN
- customer_name: the customer's name or nickname, if mentioned
- date: the booking/event date if mentioned (resolve to YYYY-MM-DD if you can infer the \
year from context, otherwise leave the date as mentioned)
- item: the item/vessel type mentioned (e.g. chairs, pathre, canopy)
- quantity: number of items, as an integer
- amount: money amount mentioned, as a number (INR)
- payment_type: "advance", "balance", or "full" - only for PAYMENT intent

IMPORTANT:
- A single utterance can contain MORE THAN ONE transaction (e.g. a booking AND a \
payment in the same sentence). Decompose these into separate transaction objects.
- If a field is not mentioned, omit it or set it to null. Do not guess values.
- Respond with ONLY a JSON object. No preamble, no explanation, no markdown code fences.

Return JSON in exactly this shape:
{
  "raw_transcript": "<the input transcript, unchanged>",
  "transactions": [
    {
      "intent": "BOOKING",
      "customer_name": "...",
      "date": "...",
      "item": "...",
      "quantity": 0,
      "amount": 0,
      "payment_type": "..."
    }
  ],
  "is_multi_intent": false,
  "confidence_note": null
}
"""


def parse_utterance(transcript: str) -> NLUResult:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": transcript}],
    )

    raw_text = response.content[0].text.strip()

    # safety net in case Claude wraps output in ```json fences despite instructions
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude did not return valid JSON:\n{raw_text}") from e

    try:
        result = NLUResult(**data)
    except ValidationError as e:
        raise ValueError(f"JSON did not match NLUResult schema:\n{e}") from e

    return result


if __name__ == "__main__":
    test_transcript = "ರಾಜುಗೆ fifteen chairs ಕೊಟ್ಟಿದ್ದೀವಿ so fifteen enter ಮಾಡಿ"

    print(f"Input transcript:\n{test_transcript}\n")

    result = parse_utterance(test_transcript)

    print("Parsed NLUResult:")
    print(result.model_dump_json(indent=2))