#Phase 2 — Requirements: Condensing user stories
from transformers import pipeline

summariser = pipeline("summarization",
                      model="facebook/bart-large-cnn",
                      min_length=30,
                      max_length=80)

user_story = """
    As a returning customer, I want to view my full order history with
    filtering by date range, product category, and order status (delivered,
    pending, cancelled), so that I can quickly locate past purchases for
    returns or reorders. The list should be paginated (20 items per page),
    support export to CSV, and display estimated delivery dates alongside
    actual delivery dates where applicable. Search by order ID or product
    name should also be available in the header.
"""

print("=== Requirements Phase: User Story Summarisation ===\n")
print("Original user story:")
print(user_story.strip())

summary = summariser(user_story)[0]["summary_text"]
print(f"\nCondensed spec (for sprint board):\n  → {summary}")