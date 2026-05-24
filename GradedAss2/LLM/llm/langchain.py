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
#  SUMMARY TABLE
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
print("  ✅  All tests complete!")
print("=" * 62)