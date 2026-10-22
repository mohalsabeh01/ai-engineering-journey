import re
from rank_bm25 import BM25Okapi
from rag_data import DOCS, QUESTIONS


STOPWORDS = {
    "am", "an", "auf", "bin", "das", "der", "die", "ein", "eine", "einem",
    "es", "gibt", "ich", "ihr", "im", "in", "ist", "kann", "mit", "nach",
    "nicht", "sie", "und", "von", "was", "wenn", "wie", "wir", "zu",
}


def tokenize(text):
    # Kleinbuchstaben, nur Wörter, ohne häufige Füllwörter
    words = re.findall(r"\w+", text.lower())
    return [w for w in words if w not in STOPWORDS]


corpus = [tokenize(doc["text"]) for doc in DOCS]
bm25 = BM25Okapi(corpus)


def search(question, k=3):
    scores = bm25.get_scores(tokenize(question))
    ranked = sorted(zip(DOCS, scores), key=lambda pair: pair[1], reverse=True)
    return [(doc, score) for doc, score in ranked[:k] if score > 0]


if __name__ == "__main__":
    hits = 0
    for q in QUESTIONS:
        results = search(q["question"])
        top_id = results[0][0]["id"] if results else None
        ok = top_id == q["expected"]
        hits += ok
        status = "TREFFER" if ok else ("NICHTS" if top_id is None else "FALSCH")
        print(f"\n{status} | {q['question']} (erwartet {q['expected']})")
        print(f"   Tokens: {tokenize(q['question'])}")
        for doc, score in results:
            print(f"   {score:5.2f}  {doc['id']}  {doc['text'][:55]}")
    print(f"\nTreffer auf Platz 1: {hits}/{len(QUESTIONS)}")