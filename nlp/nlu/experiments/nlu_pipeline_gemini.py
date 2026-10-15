"""
NLU pipeline (Gemini version): takes a codemixed Kannada-English transcript
(from Sarvam ASR) and sends it to Google Gemini to extract structured
intent + entities. Output is validated against NLUResult (see nlu_schema.py).

SETUP:
1. Get a free Gemini API key: https://aistudio.google.com/apikey
2. Add to your .env file:  GEMINI_API_KEY=your_key_here
3. pip install google-generativeai python-dotenv

Run: python nlu_pipeline_gemini.py
"""

import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
from pydantic import ValidationError

from nlu_schema import NLUResult

load_dotenv()  # reads GEMINI_API_KEY from .env

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

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

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    system_instruction=SYSTEM_PROMPT,
)


def parse_utterance(transcript: str) -> NLUResult:
    response = model.generate_content(
        transcript,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",  # forces valid JSON output
        ),
    )

    raw_text = response.text.strip()
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Gemini did not return valid JSON:\n{raw_text}") from e

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