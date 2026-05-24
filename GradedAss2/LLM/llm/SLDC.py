# ============================================================
#   SDLC — Design Phase
#   Auto-Generate Executive Design Summaries
#   Model : facebook/bart-large-cnn
#   Task  : Summarisation → Non-technical stakeholder briefs
# ============================================================

from transformers import pipeline
from datetime import datetime


# ─────────────────────────────────────────────────────────────
# 1. LOAD MODEL
# ─────────────────────────────────────────────────────────────

print("Loading summarisation model (facebook/bart-large-cnn)...")
summariser = pipeline(
    "summarization",
    model="facebook/bart-large-cnn",
)
print("Model ready.\n")


# ─────────────────────────────────────────────────────────────
# 2. SAMPLE TECHNICAL DESIGN DOCUMENTS
#    (As written by engineers / architects)
# ─────────────────────────────────────────────────────────────

design_documents = [
    {
        "title"    : "Authentication Service — Architecture Design",
        "audience" : "CTO / Product Owner",
        "content"  : """
            The authentication service will be implemented as a stateless
            microservice using OAuth 2.0 with PKCE flow for all public-facing
            clients. JWTs will be signed with RS256 asymmetric keys rotated
            every 24 hours via AWS KMS. Token expiry is set to 15 minutes for
            access tokens and 7 days for refresh tokens stored in HttpOnly
            cookies. The service will expose four REST endpoints: /token,
            /refresh, /revoke, and /introspect, all behind an NGINX API
            gateway with rate limiting of 100 requests per minute per IP.
            Redis will be used for token blacklisting with a TTL matching the
            original token expiry. Horizontal scaling is supported via
            stateless design. Expected p99 latency under load is under 120ms.
            A circuit breaker pattern via Resilience4j will prevent cascading
            failures if the identity provider becomes unavailable.
        """
    },
    {
        "title"    : "Database Schema — Order Management System",
        "audience" : "Project Manager / Business Analyst",
        "content"  : """
            The order management database will use PostgreSQL 15 with a
            normalised schema across six core tables: customers, addresses,
            products, orders, order_items, and payments. The orders table
            will carry a status ENUM with seven states: draft, confirmed,
            processing, shipped, delivered, cancelled, and refunded. Foreign
            key constraints enforce referential integrity between orders and
            customers. Indexes are applied to order status, created_at, and
            customer_id columns to support the most frequent query patterns.
            Soft deletes are implemented via a deleted_at timestamp column
            rather than physical row deletion to preserve audit history.
            Partitioning by created_at will be applied to the order_items
            table once row count exceeds five million records. Connection
            pooling is handled by PgBouncer with a max pool size of 100
            per application node. Read replicas will serve reporting queries
            to avoid contention with transactional workloads.
        """
    },
    {
        "title"    : "Frontend Architecture — Customer Portal Redesign",
        "audience" : "Marketing Director / UX Sponsor",
        "content"  : """
            The customer portal will be rebuilt as a React 18 single-page
            application using Next.js 14 with the App Router for server-side
            rendering of SEO-critical pages. State management will use Zustand
            for lightweight global state alongside React Query for server state
            and cache invalidation. Component design follows atomic design
            principles with a Storybook library of 40+ reusable components
            built on top of Radix UI primitives for accessibility compliance
            with WCAG 2.1 AA. Code splitting via dynamic imports reduces the
            initial JavaScript bundle to under 120 KB gzipped. The design
            system tokens are sourced from a Figma variables file and exported
            as CSS custom properties at build time, ensuring pixel-perfect
            parity between design and implementation. Lighthouse performance
            score target is 90+ on mobile. Deployment is via Vercel with
            preview environments generated per pull request for stakeholder
            review before merging.
        """
    },
    {
        "title"    : "API Design — Payment Integration Gateway",
        "audience" : "Finance Director / Compliance Officer",
        "content"  : """
            The payment gateway integration will use Stripe as the primary
            processor with PayPal as a failover option. Payment intents will
            be created server-side to prevent client-side manipulation of
            amounts. All card data is handled exclusively by Stripe Elements,
            ensuring the application never touches raw PAN data and maintaining
            PCI DSS SAQ A compliance. Webhooks from Stripe will be verified
            using HMAC signatures and processed via an idempotent event handler
            to prevent duplicate charges on retry. Refunds, partial captures,
            and dispute handling are exposed through an internal admin API
            restricted to staff roles. All payment events are logged to an
            append-only audit table with user ID, timestamp, amount, currency,
            and outcome. Currency conversion is handled at the Stripe level
            using dynamic currency conversion. Failed payment retry logic
            follows an exponential backoff strategy with a maximum of three
            retries over 72 hours before the order is cancelled automatically.
        """
    },
]


# ─────────────────────────────────────────────────────────────
# 3. SUMMARISATION CONFIGS PER AUDIENCE TYPE
#    Different stakeholders need different summary lengths
# ─────────────────────────────────────────────────────────────

AUDIENCE_CONFIG = {
    # C-Suite → very brief, strategic framing only
    "CTO / Product Owner"           : {"min_length": 40, "max_length": 80 },
    # PM / BA → moderate detail, enough to brief their team
    "Project Manager / Business Analyst" : {"min_length": 55, "max_length": 110},
    # Marketing / UX sponsors → outcome-focused, no jargon
    "Marketing Director / UX Sponsor"    : {"min_length": 50, "max_length": 95 },
    # Finance / Compliance → risk and regulation focus
    "Finance Director / Compliance Officer": {"min_length": 60, "max_length": 120},
}


# ─────────────────────────────────────────────────────────────
# 4. EXECUTIVE SUMMARY GENERATOR
# ─────────────────────────────────────────────────────────────

def generate_executive_summary(
    doc: dict,
    summariser_pipeline,
    audience_config: dict,
) -> dict:
    """
    Generate a non-technical executive summary from a design document.

    Parameters
    ----------
    doc               : dict with keys 'title', 'audience', 'content'
    summariser_pipeline: loaded Hugging Face summarisation pipeline
    audience_config   : dict mapping audience label to min/max_length

    Returns
    -------
    dict with original metadata plus generated 'summary' and 'generated_at'
    """
    config = audience_config.get(
        doc["audience"],
        {"min_length": 50, "max_length": 100}        # sensible default
    )

    raw_summary = summariser_pipeline(
        doc["content"].strip(),
        min_length=config["min_length"],
        max_length=config["max_length"],
        do_sample=False,                              # deterministic output
    )[0]["summary_text"]

    return {
        "title"        : doc["title"],
        "audience"     : doc["audience"],
        "summary"      : raw_summary,
        "word_count"   : len(raw_summary.split()),
        "generated_at" : datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


# ─────────────────────────────────────────────────────────────
# 5. BATCH PROCESS ALL DESIGN DOCUMENTS
# ─────────────────────────────────────────────────────────────

print("=" * 65)
print("  SDLC DESIGN PHASE — Executive Summary Generator")
print("  Model : facebook/bart-large-cnn")
print("=" * 65)

summaries = []

for doc in design_documents:
    result = generate_executive_summary(doc, summariser, AUDIENCE_CONFIG)
    summaries.append(result)

    print(f"\n{'─' * 65}")
    print(f"  Document : {result['title']}")
    print(f"  Audience : {result['audience']}")
    print(f"  Generated: {result['generated_at']}  |  Words: {result['word_count']}")
    print(f"{'─' * 65}")
    print(f"\n  {result['summary']}\n")


# ─────────────────────────────────────────────────────────────
# 6. EXPORT — MARKDOWN BRIEFING DOCUMENT
#    Ready to paste into Confluence, Notion, or email
# ─────────────────────────────────────────────────────────────

def export_to_markdown(summaries: list[dict]) -> str:
    """
    Render all executive summaries as a single Markdown briefing document.

    Parameters
    ----------
    summaries : list of summary dicts from generate_executive_summary()

    Returns
    -------
    str : full Markdown-formatted briefing document
    """
    lines = [
        "# Design Phase — Executive Briefing Document",
        f"_Auto-generated on {datetime.now().strftime('%d %B %Y')}_",
        "",
        "> This document contains non-technical summaries of all active",
        "> design documents. Full technical specifications are available",
        "> in the engineering Confluence space.",
        "",
    ]

    for s in summaries:
        lines += [
            f"## {s['title']}",
            f"**Prepared for:** {s['audience']}",
            "",
            s["summary"],
            "",
            "---",
            "",
        ]
    return "\n".join(lines)


markdown_output = export_to_markdown(summaries)

# Save to file
output_path = "executive_design_briefing.md"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(markdown_output)

print("=" * 65)
print(f"  Markdown briefing exported → {output_path}")
print(f"  Total documents summarised : {len(summaries)}")
print("=" * 65)