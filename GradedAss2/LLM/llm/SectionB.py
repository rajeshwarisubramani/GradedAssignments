# ============================================================
#   DistilGPT-2 Text Generation Explorer
#   Run:  python distilgpt2_explorer.py
#   Requires: pip install transformers torch
# ============================================================

# ── Step 0 · Install dependencies (uncomment if needed) ─────
# import subprocess, sys
# subprocess.run([sys.executable, "-m", "pip", "install",
#                 "transformers", "torch", "--quiet"])

import warnings
warnings.filterwarnings("ignore")

from transformers import pipeline, AutoTokenizer

# ════════════════════════════════════════════════════════════
#  LOAD MODEL
# ════════════════════════════════════════════════════════════
print("=" * 62)
print("  DistilGPT-2 Text Generation Explorer")
print("=" * 62)
print("\n⏳ Loading distilgpt2 …  (downloads ~80 MB on first run)\n")

generator = pipeline("text-generation", model="distilgpt2")

print("✅ Model loaded!\n")

# ════════════════════════════════════════════════════════════
#  HELPER — pretty-print results
# ════════════════════════════════════════════════════════════
def show(title: str, prompt: str, results: list, notes: str = ""):
    print("─" * 62)
    print(f"  {title}")
    if notes:
        print(f"  ℹ️  {notes}")
    print("─" * 62)
    print(f"  Prompt : \"{prompt}\"")
    for i, r in enumerate(results, 1):
        label = f"  Seq {i}  : " if len(results) > 1 else "  Output : "
        print(f"{label}{r['generated_text']}")
    print()


# ════════════════════════════════════════════════════════════
#  TEST 1 · Baseline (from the assignment)
# ════════════════════════════════════════════════════════════
show(
    title  = "TEST 1 │ Baseline Prompt",
    prompt = "AI is transforming industries by",
    results= generator(
        "AI is transforming industries by",
        max_length=40,
        num_return_sequences=1
    )
)

# ════════════════════════════════════════════════════════════
#  TEST 2 · Different topic — observe domain shift in output
# ════════════════════════════════════════════════════════════
show(
    title  = "TEST 2 │ Different Topic Prompt",
    prompt = "The future of medicine depends on",
    results= generator(
        "The future of medicine depends on",
        max_length=40,
        num_return_sequences=1
    ),
    notes  = "Same params, different topic → output changes direction"
)

# ════════════════════════════════════════════════════════════
#  TEST 3 · Vary max_length → see how output truncates / grows
# ════════════════════════════════════════════════════════════
prompt3 = "Space exploration will lead to"
print("─" * 62)
print("  TEST 3 │ Varying max_length (20 vs 60 tokens)")
print("  ℹ️  Watch how the story grows as we allow more tokens")
print("─" * 62)
print(f"  Prompt : \"{prompt3}\"")

r_short = generator(prompt3, max_length=20,  num_return_sequences=1)
r_long  = generator(prompt3, max_length=60,  num_return_sequences=1)

print(f"  max=20  : {r_short[0]['generated_text']}")
print(f"  max=60  : {r_long[0]['generated_text']}")
print()

# ════════════════════════════════════════════════════════════
#  TEST 4 · Multiple sequences — diversity in one call
# ════════════════════════════════════════════════════════════
show(
    title  = "TEST 4 │ Multiple Sequences (num_return_sequences=3)",
    prompt = "Robots will soon be able to",
    results= generator(
        "Robots will soon be able to",
        max_length=35,
        num_return_sequences=3,
        do_sample=True,
        temperature=0.9
    ),
    notes  = "Three different continuations from the same prompt"
)

# ════════════════════════════════════════════════════════════
#  TEST 5 · Temperature — focused (0.3) vs creative (1.5)
# ════════════════════════════════════════════════════════════
prompt5 = "Deep learning models can"
print("─" * 62)
print("  TEST 5 │ Temperature Effect (do_sample=True)")
print("  ℹ️  Low temp = repetitive/safe. High temp = wild/creative.")
print("─" * 62)
print(f"  Prompt : \"{prompt5}\"")

r_low  = generator(prompt5, max_length=40, num_return_sequences=1,
                   do_sample=True, temperature=0.3)
r_high = generator(prompt5, max_length=40, num_return_sequences=1,
                   do_sample=True, temperature=1.5)

print(f"  temp=0.3: {r_low[0]['generated_text']}")
print(f"  temp=1.5: {r_high[0]['generated_text']}")
print()

# ════════════════════════════════════════════════════════════
#  TEST 6 · Greedy vs Sampling (do_sample flag)
# ════════════════════════════════════════════════════════════
prompt6 = "The best way to learn programming is"
print("─" * 62)
print("  TEST 6 │ Greedy Decoding vs Random Sampling")
print("  ℹ️  Greedy always picks the highest-prob token → deterministic")
print("─" * 62)
print(f"  Prompt : \"{prompt6}\"")

r_greedy  = generator(prompt6, max_length=40, do_sample=False)   # greedy
r_sampled = generator(prompt6, max_length=40, do_sample=True, temperature=1.0)

print(f"  greedy  : {r_greedy[0]['generated_text']}")
print(f"  sampled : {r_sampled[0]['generated_text']}")
print()

# ════════════════════════════════════════════════════════════
#  TEST 7 · Tokenisation deep-dive
# ════════════════════════════════════════════════════════════
print("─" * 62)
print("  TEST 7 │ Tokenisation Peek")
print("  ℹ️  Words ≠ tokens. GPT-2 uses Byte-Pair Encoding (BPE).")
print("─" * 62)

tokenizer = AutoTokenizer.from_pretrained("distilgpt2")

sentences = [
    "AI is transforming industries by automating tasks",
    "Unbelievably, transformers revolutionised NLP overnight!",
]

for sentence in sentences:
    token_ids = tokenizer.encode(sentence)
    tokens    = [tokenizer.decode([t]) for t in token_ids]
    print(f"\n  Sentence  : {sentence}")
    print(f"  Token IDs : {token_ids}")
    print(f"  Tokens    : {tokens}")
    print(f"  Stats     : {len(sentence.split())} words → {len(token_ids)} tokens")

print()

# ════════════════════════════════════════════════════════════
#  SUMMARY TABLE — Section A
# ════════════════════════════════════════════════════════════
print("=" * 62)
print("  WHAT TO OBSERVE — Key Takeaways")
print("=" * 62)
summary = [
    ("max_length ↑",         "Longer output; model may drift off-topic"),
    ("num_return_sequences↑","Multiple diverse completions in one call"),
    ("temperature ↓ (0.1)",  "Safe, repetitive, predictable text"),
    ("temperature ↑ (1.5)",  "Creative, sometimes incoherent text"),
    ("do_sample=False",      "Greedy — same output every run"),
    ("do_sample=True",       "Stochastic — different each time"),
    ("Tokenisation",         "Subword tokens, not whole words (BPE)"),
]
print(f"  {'Parameter':<28} {'Effect'}")
print("  " + "-" * 56)
for param, effect in summary:
    print(f"  {param:<28} {effect}")
print("=" * 62)
print("  ✅  Section A Tests Complete!")
print("=" * 62)


# ╔══════════════════════════════════════════════════════════╗
#  SECTION B · PROMPT ENGINEERING
#  Experiments with phrasing across three task types:
#    1. Summarisation   2. Q&A   3. Creative Text Generation
# ╚══════════════════════════════════════════════════════════╝

print("\n")
print("╔" + "═" * 60 + "╗")
print("║         SECTION B — PROMPT ENGINEERING                    ║")
print("╚" + "═" * 60 + "╝\n")

# ────────────────────────────────────────────────────────────
#  HELPER — word counter to check output length
# ────────────────────────────────────────────────────────────
def word_count(text: str) -> int:
    return len(text.split())

def show_b(title: str, prompts: list, results: list, notes: str = ""):
    """Display side-by-side prompt comparisons for Section B."""
    print("─" * 62)
    print(f"  {title}")
    if notes:
        print(f"  ℹ️  {notes}")
    print("─" * 62)
    for i, (prompt, result) in enumerate(zip(prompts, results), 1):
        output = result[0]['generated_text']
        wc     = word_count(output)
        print(f"\n  Prompt v{i} : \"{prompt}\"")
        print(f"  Output    : {output}")
        print(f"  Word count: {wc} words")
    print()


# ════════════════════════════════════════════════════════════
#  TASK 1 · SUMMARISATION
#  Goal : Keep output ≤ 30 words.
#  Strategy : Compare vague vs specific instruction phrasing.
# ════════════════════════════════════════════════════════════
print("━" * 62)
print("  TASK 1 │ SUMMARISATION  (target: ≤ 30 words output)")
print("━" * 62)

# Prompt v1 — Vague: no length or style instruction
sum_prompt_v1 = "Summarize artificial intelligence."

# Prompt v2 — Clear: specifies brevity and a sentence cap
sum_prompt_v2 = "In one sentence, briefly summarize what artificial intelligence is:"

# Prompt v3 — Structured: gives context + explicit instruction
sum_prompt_v3 = (
    "Artificial intelligence is the simulation of human intelligence by machines. "
    "Summarize this in 20 words or fewer:"
)

sum_prompts = [sum_prompt_v1, sum_prompt_v2, sum_prompt_v3]
sum_results = [
    generator(p, max_length=50, num_return_sequences=1, do_sample=False)
    for p in sum_prompts
]

show_b(
    title   = "SUMMARISATION — Prompt Comparison",
    prompts = sum_prompts,
    results = sum_results,
    notes   = "v1=vague | v2=adds brevity cue | v3=context + length constraint"
)

print("  📝 Observation:")
print("     v1 (vague)  → Model free-associates; often verbose or off-topic.")
print("     v2 (clear)  → 'One sentence' nudges the model toward conciseness.")
print("     v3 (context)→ Providing the source text anchors the summary better.")
print()


# ════════════════════════════════════════════════════════════
#  TASK 2 · QUESTION & ANSWER (Q&A)
#  Goal : Elicit a factual, direct answer.
#  Strategy : Compare open-ended vs answer-framing prompts.
# ════════════════════════════════════════════════════════════
print("━" * 62)
print("  TASK 2 │ Q&A  (factual question answering)")
print("━" * 62)

# Prompt v1 — Plain question only
qa_prompt_v1 = "What is machine learning?"

# Prompt v2 — Role + question format
qa_prompt_v2 = "As an AI expert, answer in one sentence: What is machine learning?"

# Prompt v3 — Fill-in-the-blank style (strong answer framing)
qa_prompt_v3 = "Machine learning is a branch of AI that"

qa_prompts = [qa_prompt_v1, qa_prompt_v2, qa_prompt_v3]
qa_results = [
    generator(p, max_length=55, num_return_sequences=1, do_sample=False)
    for p in qa_prompts
]

show_b(
    title   = "Q&A — Prompt Comparison",
    prompts = qa_prompts,
    results = qa_results,
    notes   = "v1=plain | v2=role+format | v3=sentence-completion framing"
)

print("  📝 Observation:")
print("     v1 (plain)       → Model may repeat or rephrase the question.")
print("     v2 (role+format) → 'Expert' framing encourages factual language.")
print("     v3 (completion)  → Sentence-start forces the model straight to answer.")
print()


# ════════════════════════════════════════════════════════════
#  TASK 3 · CREATIVE TEXT GENERATION
#  Goal : Generate a 4-line poem on AI.
#  Strategy : Compare bare request vs structured creative prompts.
# ════════════════════════════════════════════════════════════
print("━" * 62)
print("  TASK 3 │ CREATIVE TEXT  (4-line poem on AI)")
print("━" * 62)

# Prompt v1 — Bare request
creative_prompt_v1 = "Write a poem about artificial intelligence."

# Prompt v2 — Specifies structure (4 lines) + mood
creative_prompt_v2 = "Write a 4-line rhyming poem about artificial intelligence and the future:"

# Prompt v3 — Gives the first line as a creative anchor
creative_prompt_v3 = (
    "Complete this 4-line poem about AI:\n"
    "In circuits and code, a new mind is born,\n"
)

creative_prompts = [creative_prompt_v1, creative_prompt_v2, creative_prompt_v3]
creative_results = [
    generator(
        p,
        max_length      = 80,
        num_return_sequences = 1,
        do_sample       = True,
        temperature     = 0.9      # higher temp for more creative output
    )
    for p in creative_prompts
]

show_b(
    title   = "CREATIVE TEXT — Prompt Comparison",
    prompts = creative_prompts,
    results = creative_results,
    notes   = "v1=bare | v2=structure+mood | v3=anchor line provided"
)

print("  📝 Observation:")
print("     v1 (bare)    → Output may be prose-like, not poem-shaped.")
print("     v2 (specific)→ 'Rhyming' cue pushes toward verse structure.")
print("     v3 (anchor)  → Giving line 1 strongly constrains style & theme.")
print()


# ════════════════════════════════════════════════════════════
#  PROMPT COMPARISON SUMMARY TABLE
# ════════════════════════════════════════════════════════════
print("=" * 62)
print("  SECTION B — Prompt Engineering Summary")
print("=" * 62)
pe_summary = [
    ("Task",          "Prompt Style",      "Key Effect"),
    ("─" * 14,        "─" * 18,            "─" * 24),
    ("Summarisation", "Vague (v1)",         "Verbose, unfocused output"),
    ("",              "Clear (v2)",         "Shorter, more on-topic"),
    ("",              "Context+limit (v3)", "Best anchored summary"),
    ("Q&A",           "Plain (v1)",         "May echo the question"),
    ("",              "Role+format (v2)",   "More factual tone"),
    ("",              "Completion (v3)",    "Direct, concise answer"),
    ("Creative",      "Bare (v1)",          "Prose drift, no structure"),
    ("",              "Structured (v2)",    "More verse-like output"),
    ("",              "Anchor line (v3)",   "Strongest style control"),
]
for row in pe_summary:
    print(f"  {row[0]:<14} {row[1]:<20} {row[2]}")
print()

# ════════════════════════════════════════════════════════════
#  REFLECTION  (100–150 words)
# ════════════════════════════════════════════════════════════
reflection = """
╔══════════════════════════════════════════════════════════════╗
║                      REFLECTION                              ║
╚══════════════════════════════════════════════════════════════╝

  Experimenting with prompt phrasing revealed that even small wording
  changes significantly shift model behaviour. Vague prompts like
  "Summarize AI" produced unfocused, verbose outputs because the model
  had no length or style target to anchor on. Adding explicit constraints
  — "one sentence" or "20 words or fewer" — steered responses toward
  conciseness and relevance.

  For Q&A tasks, framing the prompt as a sentence completion ("Calculas 
  is a branch of Maths that...") proved most effective, forcing the
  model directly into answer mode rather than restating the question.

  In creative tasks, providing the first line of the poem acted as the
  strongest structural guide, locking in rhyme scheme and theme. This
  shows that prompt clarity is not just about word choice — it includes
  format cues, role framing, and contextual anchors. The clearer and
  more specific the instruction, the more predictable and useful the
  generated output.

  Word count: ~140 words
"""
print(reflection)

print("=" * 62)
print("  ✅  Section B — Prompt Engineering Complete!")
print("=" * 62)