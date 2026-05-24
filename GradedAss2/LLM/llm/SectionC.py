# ============================================================
#   Embeddings with Gensim
#   - Word Embeddings (GloVe: glove-wiki-gigaword-50)
#   - Sentence-Level Embeddings (Average Word Vectors)
# ============================================================

import gensim.downloader as api
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import warnings
warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────────────────────
# 1. LOAD PRE-TRAINED GloVe MODEL
# ─────────────────────────────────────────────────────────────

print("Loading GloVe embeddings (glove-wiki-gigaword-50)...")
model = api.load("glove-wiki-gigaword-50")
print(f"Model loaded! Vocabulary size: {len(model)}, Vector size: {model.vector_size}\n")


# ─────────────────────────────────────────────────────────────
# 2. WORD EMBEDDINGS
# ─────────────────────────────────────────────────────────────

selected_words = ["king", "queen", "diamond"]

print("=" * 60)
print("SECTION 1: WORD EMBEDDINGS")
print("=" * 60)

for word in selected_words:

    print(f"Word: '{word}'")
    print(f"{'─' * 40}")

    # ── First 10 values of the word vector
    vector = model[word]
    print(f"\n  First 10 values of vector:")
    print(f"  {np.round(vector[:10], 4)}")

    # ── Top 5 most similar words
    similar_words = model.most_similar(word, topn=5)
    print(f"\n  Top 5 most similar words:")
    print(f"  {'Word':<20} {'Similarity Score':>16}")
    print(f"  {'----':<20} {'----------------':>16}")
    for sim_word, score in similar_words:
        print(f"  {sim_word:<20} {score:>16.4f}")

print("\n")


# ─────────────────────────────────────────────────────────────
# 3. SENTENCE-LEVEL EMBEDDINGS
# ─────────────────────────────────────────────────────────────

sentences = [
    "Artificial intelligence is transforming the world",
    "Machine learning models learn patterns from data",
    "Diamonds are the hardest natural material on earth",
    "Gold and silver are precious metals used in jewellery",
    "Deep learning enables computers to understand images",
]

print("=" * 60)
print("SECTION 2: SENTENCE-LEVEL EMBEDDINGS")
print("=" * 60)


def get_sentence_vector(sentence: str, glove_model) -> np.ndarray:
    """
    Compute a sentence vector by averaging the GloVe vectors
    of all known words in the sentence.

    Parameters
    ----------
    sentence    : Raw sentence string.
    glove_model : Loaded Gensim KeyedVectors model.

    Returns
    -------
    np.ndarray  : Mean word vector (zeros if no known words found).
    """
    tokens = sentence.lower().split()
    # Keep only tokens that exist in the vocabulary
    valid_vectors = [glove_model[token] for token in tokens if token in glove_model]

    if valid_vectors:
        return np.mean(valid_vectors, axis=0)          # Average pooling
    else:
        return np.zeros(glove_model.vector_size)       # Fallback: zero vector


# ── Compute sentence vectors
print("\nSentences used:")
sentence_vectors = []
for i, sentence in enumerate(sentences, 1):
    vec = get_sentence_vector(sentence, model)
    sentence_vectors.append(vec)
    print(f"  S{i}: {sentence}")

sentence_matrix = np.array(sentence_vectors)          # Shape: (5, 50)


# ── Cosine Similarity Matrix
similarity_matrix = cosine_similarity(sentence_matrix)

print(f"\n{'─' * 60}")
print("Cosine Similarity Matrix (Sentences vs Sentences):")
print(f"{'─' * 60}\n")

# Header row
header = f"{'':6}" + "".join(f"  S{i:<6}" for i in range(1, len(sentences) + 1))
print(header)
print("  " + "─" * (len(header) - 2))

# Matrix rows
for i, row in enumerate(similarity_matrix):
    row_str = f"  S{i+1:<4}" + "".join(f"  {score:.4f}" for score in row)
    print(row_str)

print(f"\n{'─' * 60}")
print("Interpretation Guide:")
print("  Score ~1.00  → Very high similarity")
print("  Score ~0.75  → Moderate similarity")
print("  Score ~0.50  → Low similarity")
print("  Score ~0.00  → No similarity")
print(f"{'─' * 60}\n")


# ── Most and Least Similar Sentence Pairs
print("Top 3 Most Similar Sentence Pairs:")
pairs = []
for i in range(len(sentences)):
    for j in range(i + 1, len(sentences)):
        pairs.append((similarity_matrix[i][j], i + 1, j + 1))

pairs.sort(reverse=True)

for score, i, j in pairs[:3]:
    print(f"  S{i} ↔ S{j}  |  Score: {score:.4f}")
    print(f"    S{i}: {sentences[i-1]}")
    print(f"    S{j}: {sentences[j-1]}\n")

print("Top 3 Least Similar Sentence Pairs:")
for score, i, j in pairs[-3:]:
    print(f"  S{i} ↔ S{j}  |  Score: {score:.4f}")
    print(f"    S{i}: {sentences[i-1]}")
    print(f"    S{j}: {sentences[j-1]}\n")