#Phase 1 — Planning: Stakeholder survey analysis

from transformers import pipeline

analyser = pipeline("sentiment-analysis",
                    model="distilbert-base-uncased-finetuned-sst-2-english")

# Stakeholder responses collected during the planning workshop
stakeholder_feedback = [
    "The current checkout flow is painfully slow and confusing.",
    "I love how the dashboard gives me instant visibility.",
    "Reporting takes forever and the exports never work correctly.",
    "The mobile experience is much better than last quarter.",
    "We desperately need offline mode — the app is useless without internet.",
]

print("=== Planning Phase: Stakeholder Sentiment Analysis ===\n")
results = analyser(stakeholder_feedback)

for text, result in zip(stakeholder_feedback, results):
    tag   = result["label"]
    score = result["score"]
    flag  = "⚠ Prioritise" if tag == "NEGATIVE" and score > 0.90 else ""
    print(f"[{tag:<8} | {score:.2f}] {flag}")
    print(f"  → {text}\n")