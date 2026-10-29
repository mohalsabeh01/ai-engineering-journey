from sentence_transformers import SentenceTransformer
from rag_data import DOCS, QUESTIONS

model = SentenceTransformer("intfloat/multilingual-e5-small")

doc_texts = ["passage: " + d["text"] for d in DOCS]
doc_vecs = model.encode(doc_texts, normalize_embeddings=True)


def search(question, k=3):
    q_vec = model.encode(["query: " + question], normalize_embeddings=True)[0]
    scores = doc_vecs @ q_vec
    order = scores.argsort()[::-1][:k]
    return [(scores[i], DOCS[i]) for i in order]


tests = QUESTIONS + [{"question": "Wie ist das Wetter morgen?", "expected": None}]

for q in tests:
    print(f"\n{q['question']}  (erwartet {q['expected']})")
    for s, d in search(q["question"]):
        print(f"   {s:.3f}  {d['id']}  {d['text'][:50]}")