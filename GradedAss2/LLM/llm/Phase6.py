#Phase 6 — Deployment: Auto-generated release notes

from transformers import pipeline

summariser = pipeline("summarization",
                      model="facebook/bart-large-cnn",
                      min_length=40,
                      max_length=100)

commit_log = """
    - feat: Add CSV export to order history page with date and category filters
    - fix: Resolve crash on settings page when user has no profile photo set
    - perf: Lazy-load product images on homepage reducing LCP by 400ms
    - fix: Correct incorrect delivery date display for international shipments
    - feat: Introduce offline mode with local cache for the last 50 orders
    - chore: Upgrade React from 18.1 to 18.3, update all peer dependencies
    - fix: Prevent data wipe on logout — persist local draft state to storage
"""

print("=== Deployment Phase: Auto Release Notes Generation ===\n")
print("Commit log (raw):")
print(commit_log.strip())

notes = summariser(commit_log)[0]["summary_text"]
print(f"\nGenerated release notes:\n  {notes}")