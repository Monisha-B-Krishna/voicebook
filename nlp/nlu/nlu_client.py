"""
NLU client: sends a transcript to an LLM (Claude, Groq, or local Ollama)
and returns a validated NLUResult. Swap backends by changing BACKEND below,
or by passing backend= when calling parse_utterance().

SETUP (only need the .env key for whichever backend you use):
  ANTHROPIC_API_KEY=...   (for Claude - needs paid credits)
  GROQ_API_KEY=...        (for Groq - free tier, larger models)
  (Ollama needs no key - just needs `ollama serve` running locally)

pip install anthropic groq ollama python-dotenv pydantic
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))  # project root


import os
import re
import json
from datetime import datetime
from dotenv import load_dotenv
from pydantic import ValidationError

from shared.schemas.nlu_schema import NLUResult

load_dotenv()

# Change this to switch backends: "claude", "groq", or "ollama"
BACKEND = "ollama"

SYSTEM_PROMPT = """You are the NLU layer for VoiceBook, a voice assistant for a \
Kannada-speaking tent house (event equipment rental) owner in Bengaluru.

You will receive a transcript of the owner's speech, in code-mixed Kannada-English \
(Kannada words in Kannada script, English words in Latin script).

Your job: extract one or more structured transactions from the utterance.

Each transaction has:
- intent: one of BOOKING, PAYMENT, RETURN, QUERY, UNKNOWN

IMPORTANT - disambiguating BOOKING vs RETURN: words like "kottiddivi"/"kotta"/"given" \
are AMBIGUOUS on their own - they can describe items going OUT (owner issuing items to \
a customer for an event = BOOKING) or, less commonly, items coming back. Default to \
BOOKING whenever items are being given/issued with no other signal. Only classify as \
RETURN when there is an EXPLICIT signal that items are coming BACK from the customer \
to the store - words like "return", "vapas", "tirugi", "tandidru", "waapas kotta". If \
you don't see one of those explicit return-signal words, it's a BOOKING, not a RETURN, \
even if the sentence uses "given/kotta" language.
- customer_name: the customer's name or nickname, if mentioned. IMPORTANT: each \
transaction has its OWN customer_name - do not assume every transaction in the \
utterance is for the same person. If the utterance mentions a different name partway \
through (e.g. "Raju ge 50 chair book maadidaare, Raju anna ge 10 plates book aagide"), \
each transaction gets the customer_name that was actually stated closest to it, even \
if that means two transactions in the same output have two different customer_names. \
Never leave customer_name null just because a different name appeared earlier in the \
utterance for a different transaction.
- date: the booking/event date if a month+day are mentioned (e.g. "June 15"), OR if \
a relative day word is used ("today", "tomorrow", "yesterday", "ಇವತ್ತು", "ನಾಳೆ", \
"ನಿನ್ನೆ"). For relative day words, just note that a date was mentioned - the exact \
date will be computed automatically downstream from the system clock, so you don't \
need to calculate it yourself; any placeholder YYYY-MM-DD is fine, it will be \
overridden. If NO date evidence at all is mentioned (no month, no day, no relative \
word), set date to null - do not invent a date from nothing.
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
- If a SINGLE booking/return mentions MULTIPLE DIFFERENT ITEMS, each with its own \
quantity (e.g. "30 chairs, 20 pathre booked" = two different items, two different \
quantities), create a SEPARATE transaction for EACH item - same intent, same \
customer, same date, but item and quantity specific to that item. NEVER merge \
multiple items into one string like "chairs and pathre" and NEVER leave quantity \
null when a number was clearly stated for each item - each number belongs to its \
own item, split them out.
- If a field is not mentioned, set it to null. NEVER substitute 0 (zero) for a missing \
amount or quantity - null means "not mentioned", 0 means "explicitly stated as zero". \
Do not guess or infer any value that is not stated in the utterance.
- Keep customer_name and item names in Latin/Roman script transliteration if they \
were spoken as English words or common nicknames (e.g. "Raju" not "ರಾಜು", "chairs" not \
"ಚೇರ್‌ಗಳು"), even if the transcript itself shows Kannada script for them.
- CONSISTENCY: if the same item is mentioned more than once in the utterance (even \
with slightly different pronunciation or spelling each time, e.g. "ಚೇರು" once and \
"ಚೇರ್" later), use the EXACT SAME item name every time it appears in your output. Do \
not produce two different spellings ("cheeru" and "chair") for what is clearly the \
same item - pick one consistent spelling and use it throughout.
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


def _call_claude(transcript: str) -> str:
    from anthropic import Anthropic
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": transcript}],
    )
    return response.content[0].text.strip()


def _call_groq(transcript: str) -> str:
    from groq import Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": transcript},
        ],
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content.strip()


def _call_ollama(transcript: str) -> str:
    import ollama
    response = ollama.chat(
        model="llama3.2:3b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": transcript},
        ],
        format="json",
    )
    return response["message"]["content"].strip()


BACKEND_FUNCS = {
    "claude": _call_claude,
    "groq": _call_groq,
    "ollama": _call_ollama,
}


from datetime import timedelta

YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")
DATE_PATTERN = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
MONTH_PATTERN = re.compile(
    r"\b(jan(uary)?|feb(ruary)?|mar(ch)?|apr(il)?|may|jun(e)?|jul(y)?|"
    r"aug(ust)?|sep(t|tember)?|oct(ober)?|nov(ember)?|dec(ember)?)\b",
    re.IGNORECASE,
)

# Relative day words, in English and common Kannada spellings, mapped to a
# day offset from entry_timestamp. These are genuinely spoken words with a
# clear, unambiguous meaning - not guesses.
RELATIVE_DAY_WORDS = {
    "today": 0, "ಇವತ್ತು": 0, "ivattu": 0,
    "tomorrow": 1, "ನಾಳೆ": 1, "naale": 1,
    "yesterday": -1, "ನಿನ್ನೆ": -1, "ninne": -1,
}
RELATIVE_DAY_PATTERN = re.compile(
    "|".join(re.escape(w) for w in RELATIVE_DAY_WORDS), re.IGNORECASE
)


def _detect_relative_day_offset(transcript: str):
    """Returns a day offset (int) if a relative day word is found, else None."""
    match = RELATIVE_DAY_PATTERN.search(transcript.lower())
    if not match:
        return None
    return RELATIVE_DAY_WORDS[match.group(0).lower()]


def _transcript_has_explicit_year(transcript: str) -> bool:
    """
    A 4-digit number alone isn't proof of a spoken year - "2000 rupees" or
    "2000 advance" also matches a naive year regex. We only trust it as a real
    year if it appears within a short window of an actual month name (e.g.
    "June 2027", "2027 June") - that's the only case where the owner is
    plausibly stating a full calendar date with year.
    """
    month_match = MONTH_PATTERN.search(transcript)
    if not month_match:
        return False

    window_start = max(0, month_match.start() - 15)
    window_end = min(len(transcript), month_match.end() + 15)
    nearby_text = transcript[window_start:window_end]

    return bool(YEAR_PATTERN.search(nearby_text))


def _resolve_dates(data: dict, transcript: str, entry_dt: datetime) -> dict:
    """
    Resolves the 'date' field on every transaction using real evidence from
    the transcript, rather than trusting the model's guess:

    1. Relative day word found ("today"/"ಇವತ್ತು" etc.) -> compute the actual
       date from entry_dt + offset, override completely regardless of what
       the model produced.
    2. Month name found (e.g. "June 15") -> trust the model's month/day, but
       replace the year with entry_dt's year unless a year was genuinely
       stated near the month.
    3. Neither found -> no real evidence for any date. Force date to null,
       discarding whatever the model invented.
    """
    relative_offset = _detect_relative_day_offset(transcript)
    month_mentioned = MONTH_PATTERN.search(transcript) is not None

    if relative_offset is not None:
        resolved_date = (entry_dt + timedelta(days=relative_offset)).strftime("%Y-%m-%d")
        for txn in data.get("transactions", []):
            txn["date"] = resolved_date

    elif month_mentioned:
        transcript_has_year = _transcript_has_explicit_year(transcript)
        current_year = entry_dt.year
        for txn in data.get("transactions", []):
            date_val = txn.get("date")
            if date_val:
                match = DATE_PATTERN.match(date_val)
                if match and not transcript_has_year:
                    _, month, day = match.groups()
                    txn["date"] = f"{current_year}-{month}-{day}"
                # if a year genuinely was stated, leave the model's date as-is

    else:
        # No month name, no relative day word - there is no real evidence
        # for a date. Discard anything the model invented.
        for txn in data.get("transactions", []):
            txn["date"] = None

    return data


def parse_utterance(transcript: str, backend: str = None) -> NLUResult:
    backend = backend or BACKEND
    if backend not in BACKEND_FUNCS:
        raise ValueError(f"Unknown backend '{backend}'. Choose from: {list(BACKEND_FUNCS)}")

    raw_text = BACKEND_FUNCS[backend](transcript)
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"[{backend}] did not return valid JSON:\n{raw_text}") from e

    data["raw_transcript"] = transcript
    entry_dt = datetime.now()
    data["entry_timestamp"] = entry_dt.isoformat()
    data = _resolve_dates(data, transcript, entry_dt)

    # is_multi_intent should be a deterministic fact about the output, not
    # something we trust the model to compute correctly - it's simply
    # "are there more than one transactions", regardless of whether the
    # model got this flag right in its own JSON.
    data["is_multi_intent"] = len(data.get("transactions", [])) > 1

    try:
        result = NLUResult(**data)
    except ValidationError as e:
        raise ValueError(f"[{backend}] JSON did not match schema:\n{raw_text}\n\nError:\n{e}") from e

    return result


if __name__ == "__main__":
    test_transcript = "Raju ge June 15 ge 50 pathre booking maadidaare, 2000 advance kottidaare"
    print(f"Backend: {BACKEND}")
    print(f"Input: {test_transcript}\n")
    result = parse_utterance(test_transcript)
    print(result.model_dump_json(indent=2))