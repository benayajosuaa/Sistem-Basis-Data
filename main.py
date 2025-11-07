from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from qdrant_client.models import Filter
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv
import requests

# ======================
# CONFIG
# ======================
QDRANT_URL = "http://localhost:6333"   # pastikan Qdrant jalan di Docker lokal
COLLECTION_NAME = "recipes"

# === LOAD .env dan API KEY ===
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "❌ GEMINI_API_KEY belum diset.\n"
        "Tambahkan ke file .env seperti ini:\n"
        "GEMINI_API_KEY=your_key"
    )

# ======================
# KONFIGURASI GEMINI (langsung pakai HTTP v1beta)
# ======================
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

def ask_gemini(prompt: str) -> str:
    """Kirim prompt langsung ke Gemini 2.0 Flash via HTTP (tanpa library Google)"""
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GEMINI_API_KEY
    }
    data = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }

    try:
        response = requests.post(GEMINI_ENDPOINT, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"[Error Gemini API] {e}"

# ======================
# LOAD DATASET
# ======================
print("🔹 Loading dataset...")

with open("recipes_final.txt", "r", encoding="utf-8") as f:
    raw_text = f.read()

texts = [t.strip() for t in raw_text.split("\n") if t.strip()]
names = [t[:30] + "..." for t in texts]

print(f"📚 Loaded {len(texts)} recipes/snippets dari file teks.")

# ======================
# LOAD EMBEDDING MODEL
# ======================
print("🔹 Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")  # dim = 384

# ======================
# CONNECT QDRANT
# ======================
client = QdrantClient(QDRANT_URL)

print("🔹 Setting up Qdrant collection...")
if not client.collection_exists(COLLECTION_NAME):
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )
else:
    print("ℹ️ Collection sudah ada, skip pembuatan ulang.")

# ======================
# EMBEDDING DAN UPLOAD
# ======================
print("🔹 Generating embeddings...")
vectors = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)

print("🔹 Uploading vectors ke Qdrant...")
points = [
    PointStruct(
        id=i,
        vector=vectors[i].tolist(),
        payload={"recipe_name": names[i], "directions": texts[i]},
    )
    for i in range(len(vectors))
]

client.upsert(collection_name=COLLECTION_NAME, points=points)
print(f"✅ {len(points)} recipes uploaded ke Qdrant!")

# ======================
# QUERY FUNCTION (RAG)
# ======================
def query_recipes(user_query: str):
    """Cari kemiripan resep dari Qdrant dan kirim ke Gemini"""
    print(f"\n🔍 Searching for: {user_query}")
    q_vector = model.encode([user_query])[0]

    # 🔧 FIX: Gunakan search() (stabil di semua versi)
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=q_vector.tolist(),
        limit=3
    )

    if not results:
        print("⚠️ Tidak ada hasil mirip ditemukan di database.")
        return

    context = "\n\n".join(
        f"{r.payload.get('recipe_name', 'Unknown')}\n{r.payload.get('directions', '')}"
        for r in results
    )

    prompt = f"""
Kamu adalah asisten masak yang ringkas dan to the point.

Konteks resep terkait (hasil retrieval):
{context}

Tugas:
- Jawab pertanyaan pengguna berikut secara detail, jelas, dan dalam bahasa Indonesia.
- Jika instruksi tidak cukup di konteks, beri saran praktis (tandai sebagai saran umum).

Pertanyaan pengguna:
\"\"\"{user_query}\"\"\"
"""
    answer = ask_gemini(prompt)
    print("\n🤖 Jawaban Gemini:")
    print(answer)


# ======================
# CLI LOOP
# ======================
if __name__ == "__main__":
    while True:
        q = input("\n🧠 Masukkan pertanyaan (atau ketik 'exit' untuk keluar): ")
        if q.lower().strip() == "exit":
            print("👋 Keluar dari sistem.")
            break
        query_recipes(q)
