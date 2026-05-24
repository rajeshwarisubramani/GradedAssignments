#Phase 5 — Testing: Automated bug triage
from transformers import pipeline

analyser = pipeline("sentiment-analysis",
                    model="distilbert-base-uncased-finetuned-sst-2-english")

bug_reports = [
    {"id": "BUG-101", "text": "App crashes every time I open the settings page."},
    {"id": "BUG-102", "text": "The new filter works fine but could load a bit faster."},
    {"id": "BUG-103", "text": "Absolutely broken — data gets wiped after logout!"},
    {"id": "BUG-104", "text": "Minor alignment issue on the profile avatar."},
]

print("=== Testing Phase: Bug Report Triage ===\n")
print(f"{'ID':<10} {'Severity':<12} {'Score':<8} Description")
print("-" * 70)

critical, normal = [], []

for report in bug_reports:
    result   = analyser(report["text"])[0]
    label    = result["label"]
    score    = result["score"]
    severity = "CRITICAL" if label == "NEGATIVE" and score > 0.95 else "NORMAL"

    if severity == "CRITICAL":
        critical.append(report["id"])

    print(f"{report['id']:<10} {severity:<12} {score:.4f}  {report['text'][:45]}...")

print(f"\n{len(critical)} critical bug(s) flagged for immediate escalation: {critical}")