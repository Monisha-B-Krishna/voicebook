"""
NLU pipeline (Ollama / local model version): takes a codemixed
Kannada-English transcript (from Sarvam ASR) and sends it to a local
LLM running via Ollama to extract structured intent + entities.
Output is validated against NLUResult (see nlu_schema.py).

SETUP (already done if you followed along):
1. Install Ollama: https://ollama.com/download
2. Pull a small model:  ollama pull llama3.2:3b
3. pip install ollama

No API key needed - runs fully on your laptop.

Run: python nlu_pipeline_ollama.py
"""

import json
import ollama
from pydantic import ValidationError

from nlu_schema import NLUResult

MODEL_NAME = "llama3.2:3b"  # change if you pulled a different model

SYSTEM_PROMPT = """You are the NLU layer for VoiceBook, a voice assistant for a \
Kannada-speaking tent house (event equipment rental) owner in Bengaluru.

You will receive a transcript of the owner's speech, in code-mixed Kannada-English \
(Kannada words in Kannada script, English words in Latin script).

Your job: extract one or more structured transactions from the utterance.

Each transaction has:
- intent: one of BOOKING, PAYMENT, RETURN, QUERY, UNKNOWN
- customer_name: the customer's name or nickname, if mentioned
- date: the booking/event date if mentioned. ONLY output YYYY-MM-DD format if the \
utterance explicitly states a year. If no year is mentioned, set date to null - do NOT \
invent or guess a year under any circumstances.
- item: the item/vessel type mentioned (e.g. chairs, pathre, canopy)
- quantity: number of items, as an integer
- amount: money amount mentioned, as a number (INR)
- payment_type: "advance", "balance", or "full" - only for PAYMENT intent

IMPORTANT:
- Only create a SEPARATE transaction if the utterance clearly mentions a second, \
distinct action - for example an explicit money amount for a payment, or an explicit \
return of items. Do NOT invent a PAYMENT transaction just because a number appears in \
the sentence - a quantity of items (chairs, vessels, pathre) is NOT a payment amount.
- Most utterances contain exactly ONE transaction. Only split into multiple \
transactions when you are confident the utterance genuinely describes two different \
actions (e.g. "50 pathre booking maadidaare, 2000 advance kottidaare" = a booking of \
50 pathre AND a payment of 2000 - these are two clearly separate numbers for two \
clearly separate things).
- If a field is not mentioned, set it to null. NEVER substitute 0 (zero) for a missing \
amount or quantity - null means "not mentioned", 0 means "explicitly stated as zero". \
Do not guess or infer any value that is not stated in the utterance.
- Keep customer_name and item names in Latin/Roman script transliteration if they \
were spoken as English words or common nicknames (e.g. "Raju" not "ರಾಜು", "chairs" not \
"ಚೇರ್‌ಗಳು"), even if the transcript itself shows Kannada script for them.
- Respond with ONLY a JSON object. No preamble, no explanation, no markdown code fences.

Return JSON in exactly this shape (do NOT include raw_transcript - that is added \
automatically outside your response):
{
  "transactions": [
    {
      "intent": "BOOKING",
      "customer_name": "...",
      "date": null,
      "item": "...",
      "quantity": null,
      "amount": null,
      "payment_type": null
    }
  ],
  "is_multi_intent": false,
  "confidence_note": null
}
"""


def parse_utterance(transcript: str) -> NLUResult:
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": transcript},
        ],
        format="json",  # asks Ollama to constrain output to valid JSON
    )

    raw_text = response["message"]["content"].strip()
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON:\n{raw_text}") from e

    # We set raw_transcript ourselves from the original input, rather than trusting
    # the model to echo it back - small models sometimes corrupt text when asked to
    # repeat it verbatim, so this removes that failure mode entirely.
    data["raw_transcript"] = transcript

    try:
        result = NLUResult(**data)
    except ValidationError as e:
        raise ValueError(f"JSON did not match NLUResult schema:\n{raw_text}\n\nError:\n{e}") from e

    return result


if __name__ == "__main__":
    test_cases = [
        # Single-intent: should produce exactly ONE transaction, no invented payment
        "ರಾಜುಗೆ fifteen chairs ಕೊಟ್ಟಿದ್ದೀವಿ so fifteen enter ಮಾಡಿ",
        # Genuine multi-intent: booking + payment in one utterance
        "Raju ge June 15 ge 50 pathre booking maadidaare, 2000 advance kottidaare",
    ]

    for i, transcript in enumerate(test_cases, 1):
        print(f"--- Test {i} ---")
        print(f"Input transcript:\n{transcript}\n")
        print("Sending to local model - this may take a few seconds...\n")

        result = parse_utterance(transcript)

        print("Parsed NLUResult:")
        print(result.model_dump_json(indent=2))
        print()