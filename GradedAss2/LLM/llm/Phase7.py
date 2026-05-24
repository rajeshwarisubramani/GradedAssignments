#Phase 7 — Maintenance: Localising error messages

from transformers import pipeline

# Build a multi-language error message localiser
TARGET_LANGUAGES = {
    "French"   : "Helsinki-NLP/opus-mt-en-fr",
    "Spanish"  : "Helsinki-NLP/opus-mt-en-es",
    "German"   : "Helsinki-NLP/opus-mt-en-de",
}

ERROR_MESSAGES = [
    "Your session has expired. Please log in again.",
    "Payment failed. Check your card details and try again.",
    "File upload limit exceeded. Maximum size is 10 MB.",
]

print("=== Maintenance Phase: Error Message Localisation ===\n")

for lang, model_name in TARGET_LANGUAGES.items():
    translator = pipeline("translation", model=model_name)
    print(f"--- {lang} ---")
    for msg in ERROR_MESSAGES:
        result = translator(msg, max_length=128)[0]["translation_text"]
        print(f"  EN: {msg}")
        print(f"  {lang[:2].upper()}: {result}\n")