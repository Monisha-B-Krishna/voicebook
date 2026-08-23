"""
Quick coverage test: runs one example of each intent type (BOOKING, PAYMENT,
RETURN, QUERY) plus a multi-intent sentence through the NLU pipeline, so you
can eyeball correctness across your full intent range in one go.

Run: python test_all_intents.py --backend groq
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))  # project root


import argparse
from nlp.nlu.nlu_client import parse_utterance

TEST_SENTENCES = {
    "BOOKING": "Raju ge June 15 ge 50 pathre booking maadidaare",
    "PAYMENT": "Suresh 2000 rupees advance kottidaare",
    "RETURN": "Ramesh fifty chairs kotta, avaru forty return madidru",
    "QUERY": "Suresh estu baaki haakidaane?",
    "MULTI-INTENT": "Raju ge June 15 ge 50 pathre booking maadidaare, 2000 advance kottidaare",
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["claude", "groq", "ollama"], default=None)
    args = parser.parse_args()

    for label, sentence in TEST_SENTENCES.items():
        print(f"\n{'='*60}")
        print(f"{label}: {sentence}")
        print(f"{'='*60}")
        try:
            result = parse_utterance(sentence, backend=args.backend)
            print(result.model_dump_json(indent=2))
        except Exception as e:
            print(f"FAILED: {e}")
