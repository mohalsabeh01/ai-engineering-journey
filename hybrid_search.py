from bm25_search import search as bm25_search
from embed_search import search as embed_search
from rag_data import QUESTIONS

K = 60


def hybrid_search(question, k=3):
    scores = {}
    docs = {}
    for results in (bm25_search(question, k), embed_search(question, k)):
        for rank, (doc, _score) in enumerate(results, start=1):
            scores[doc["id"]] = scores.get(doc["id"], 0) + 1 / (K + rank)
            docs[doc["id"]] = doc
    ranked = sorted(scores, key=scores.get, reverse=True)[:k]
    return [(docs[i], scores[i]) for i in ranked]


if __name__ == "__main__":
    tests = QUESTIONS + [{"question": "Wie ist das Wetter morgen?", "expected": None}]
    hits = 0
    for q in tests:
        results = hybrid_search(q["question"])
        top_id = results[0][0]["id"]
        if q["expected"] and top_id == q["expected"]:
            hits += 1
        print(f"\n{q['question']}  (erwartet {q['expected']})")
        for doc, s in results:
            print(f"   {s:.4f}  {doc['id']}  {doc['text'][:50]}")
    print(f"\nTreffer auf Platz 1: {hits}/{len(QUESTIONS)}")