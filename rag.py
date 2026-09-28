from google import genai
from dotenv import load_dotenv
from google.genai.types import EmbedContentConfig
import os
import numpy as np

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

EMBEDDING_MODEL = "gemini-embedding-001"
CHAT_MODEL = "gemini-3.6-flash"

def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def embed_documents(chunks):
    embeddings = []
    for chunk in chunks:
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=chunk,
            config=EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
        )
        embeddings.append(result.embeddings[0].values)
    return embeddings

def embed_query(query):
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query,
        config=EmbedContentConfig(task_type="RETRIEVAL_QUERY")
    )
    return result.embeddings[0].values

def retrieve_top_k(query, chunks, chunk_embeddings, k=2):
    query_embedding = embed_query(query)
    similarities = [cosine_similarity(query_embedding, emb) for emb in chunk_embeddings]
    top_k_indices = np.argsort(similarities)[-k:][::-1]

    print("Top-K Ergebnisse:")
    for i in top_k_indices:
        print(f"{similarities[i]:.4f} -> {chunks[i]}")

    return [chunks[i] for i in top_k_indices]

def answer_with_rag(query, chunks, chunk_embeddings, k=2):
    top_chunks = retrieve_top_k(query, chunks, chunk_embeddings, k)
    context = "\n".join(top_chunks)

    interaction = client.interactions.create(
        model=CHAT_MODEL,
        input=f"""Beantworte die folgende Frage NUR basierend auf diesem Kontext:

{context}

Frage: {query}"""
    )
    return interaction.output_text


# --- Verwendung ---
chunks = [
    "Standardlieferung dauert 2-3 Werktage.",
    "Expresslieferung ist innerhalb von Hamburg in 24 Stunden möglich, kostet 15 Euro extra.",
    "Bestellungen über 50 Euro erhalten kostenlose Standardlieferung.",
    "Rückgaben sind innerhalb von 14 Tagen möglich.",
]

chunk_embeddings = embed_documents(chunks)

frage = "Wie lange dauert die Expresslieferung?"
antwort = answer_with_rag(frage, chunks, chunk_embeddings)
print(f"\nGemini's Antwort: {antwort}")