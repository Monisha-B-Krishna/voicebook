# VoiceBook folder structure

## The key file: shared/schemas/nlu_schema.py

This is the CONTRACT between the NLP layer (Monisha) and the Business
Logic / backend layer (Kiruba). Both sides should import from this exact
file - Monisha's NLU output is validated against it, and Kiruba's FastAPI
endpoint should validate incoming JSON against the same Pydantic model
(or a mirrored copy kept in sync with it).

## Folders

- `shared/schemas/` - the NLUResult contract. Both of you touch this.
- `nlp/asr/` - Sarvam ASR client
- `nlp/nlu/` - NLU client (Claude/Groq/Ollama backends)
- `nlp/nlu/experiments/` - old single-backend test scripts, kept for report
  evidence of backend comparison (not used in the actual pipeline anymore)
- `nlp/tts/` - Sarvam TTS client
- `nlp/audio_io/` - live mic recording
- `nlp/demo/` - local test scaffold: confirmation gate + storage + full
  pipeline wiring. This simulates the Flutter app + FastAPI backend just
  enough to test the NLP layer end-to-end. NOT the production system.
- `tests/` - intent-coverage test script
- `data/audio/` - all recorded/generated .wav files
- `data/transactions.json` - local demo storage (stand-in for Kiruba's
  PostgreSQL staging table)

## Running things

From the project root (voicebook/):

```
python -m nlp.demo.full_demo_pipeline --live --backend groq
python -m tests.test_all_intents --backend groq
```

Using `-m` (module mode) instead of running the .py file directly makes
Python resolve the package imports correctly.
