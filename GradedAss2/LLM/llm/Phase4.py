#Phase 4 — Implementation: Multilingual code comments

from transformers import pipeline

translator = pipeline("translation",
                      model="Helsinki-NLP/opus-mt-en-fr")   # English → French

# Inline docstring written by an English-speaking developer
english_docstring = """
    Validates the user's JWT token by checking its signature, expiry timestamp,
    and issuer claim. Raises AuthenticationError if the token is invalid or expired.
    Returns the decoded payload dictionary on success.
"""

print("=== Implementation Phase: Docstring Localisation (EN → FR) ===\n")
print("Original (English):")
print(english_docstring.strip())

translated = translator(english_docstring, max_length=256)[0]["translation_text"]
print(f"\nTranslated (French):\n{translated.strip()}")