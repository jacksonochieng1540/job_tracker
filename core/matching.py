"""
Resume <-> Job Description matching engine.

Approach: TF-IDF vectorization + cosine similarity.

Why TF-IDF instead of a hosted embeddings API (e.g. OpenAI text-embedding-3-small,
which the Due Diligence Copilot project uses)?
  - Zero external API cost or key required -> works out of the box for anyone
    who clones the repo.
  - Runs in a few milliseconds on a free-tier Render dyno with no GPU/heavy
    model download, unlike sentence-transformers.
  - Still gives a meaningful, explainable similarity score for this use case,
    since job descriptions and CVs are keyword/skill dense documents rather
    than free-flowing prose.

This module is intentionally isolated from Django models, views, etc. so it
can be unit-tested on its own and swapped for an embeddings-based version
later without touching the rest of the app.
"""

import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# A small stopword-ish list of extremely common resume/JD boilerplate terms
# that would otherwise dominate the "missing keywords" output without being
# useful signal (e.g. "experience", "team", "role").
GENERIC_TERMS = {
    "experience", "team", "role", "work", "years", "strong", "ability",
    "skills", "knowledge", "job", "company", "candidate", "including",
    "required", "preferred", "responsibilities", "requirements", "etc",
    "using", "environment", "join", "opportunity", "looking", "familiarity",
    "plus", "background", "excellent", "solid", "proven", "demonstrated",
    "understanding", "working", "similar", "related", "familiar",
    "need", "needed", "seeking", "seeking backend", "want", "wanted",
}


def _tokenize(text: str) -> set[str]:
    """Lowercase, strip punctuation, and return a set of word tokens."""
    words = re.findall(r"[a-zA-Z][a-zA-Z+.#]{1,}", text.lower())
    return {w for w in words if w not in GENERIC_TERMS and len(w) > 2}


def compute_match(resume_text: str, jd_text: str, top_n_keywords: int = 12):
    """
    Returns a dict:
        {
          "score": float 0-100,
          "missing_keywords": [list of terms present in the JD but not the resume]
        }
    """
    resume_text = (resume_text or "").strip()
    jd_text = (jd_text or "").strip()

    if not resume_text or not jd_text:
        return {"score": 0.0, "missing_keywords": []}

    # 1. Cosine similarity over TF-IDF vectors of the two documents.
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    tfidf_matrix = vectorizer.fit_transform([resume_text, jd_text])
    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    score = round(float(similarity) * 100, 1)

    # 2. Missing keywords: rank JD terms by TF-IDF weight (i.e. how
    #    distinctive/important they are to this JD specifically), then
    #    keep the top N that don't already appear in the resume.
    jd_vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    jd_matrix = jd_vectorizer.fit_transform([jd_text])
    feature_names = jd_vectorizer.get_feature_names_out()
    jd_scores = jd_matrix.toarray()[0]
    ranked_terms = [
        term for term, _ in sorted(zip(feature_names, jd_scores), key=lambda x: x[1], reverse=True)
    ]

    resume_tokens = _tokenize(resume_text)
    missing = []
    for term in ranked_terms:
        term_words = set(term.split())
        if term_words & GENERIC_TERMS:
            continue
        # Consider it "covered" if every word in the (possibly 2-word) term
        # already shows up somewhere in the resume.
        if not term_words.issubset(resume_tokens):
            missing.append(term)
        if len(missing) >= top_n_keywords:
            break

    return {"score": score, "missing_keywords": missing}
