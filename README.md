### **Projek Sistem Basis Data** 
Universitas Pelita Harapan

> **dikerjakan oleh :** <br/>
Benaya Simamora – 01082240013 <br/>
Darren Marvel – 01112240014 <br/>
Fronli Asian Samuel – 01082240018 <br/>
Michael Yulianto Tamba – 01082240012 <br/>
> 

---

<br/>

# RAG Resep dengan Qdrant + Gemini

Pipeline **Retrieval-Augmented Generation (RAG)** sederhana untuk menjawab pertanyaan tentang resep masakan.

Menggunakan kombinasi:

- **Qdrant** → Vector Database untuk penyimpanan embedding.
- **Sentence Transformers** → Pembuat embedding teks.
- **Gemini API** → Large Language Model untuk menjawab pertanyaan.

Dataset: `recipes_final.txt`

> Tiap baris/paragraf dianggap sebagai satu resep (dokumen independen)
> 

<br/>

## Prasyarat

- Python ≥ 3.10
- Docker (untuk Qdrant)
- API Key Gemini dari [**Google AI Studio**](https://aistudio.google.com/)

## a. Setup Proyek & Virtual Environment

```bash
# Masuk ke folder proyek
cd UAS-Sistem-Basis-Data

# Buat virtualenv (macOS/Linux)
python3 -m venv .venv
source .venv/bin/activate

# (Windows PowerShell)
# python -m venv .venv
# .venv\Scripts\Activate.ps1
```

## b. Install Dependencies

Buat file `requirements.txt`:

```
1qdrant-client
sentence-transformers
python-dotenv
requests
tqdm
```

Install semua dependensi:

```bash
pip install -r requirements.txt
```

## c. Jalankan Qdrant (Docker)

```bash
# Jalankan Qdrant di background
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant

```

Kalau port `6333` sudah dipakai:

```bash
docker ps
docker stop <container_id>
docker run -d -p 6333:6333 qdrant/qdrant

```

> Untuk penyimpanan persisten (tidak hilang setelah restart):
> 
> 
> ```bash
> docker run -d --name qdrant \
>   -p 6333:6333 \
>   -v $(pwd)/qdrant_storage:/qdrant/storage \
>   qdrant/qdrant
> 
> ```
> 

## d. Konfigurasi Environment (.env)

Buat file `.env` di root proyek:

```
GEMINI_API_KEY=MASUKKAN_API_KEY_MU_DI_SINI

```

> ⚠️ Jangan commit file .env ke git. Tambahkan ke .gitignore.
> 

## e. Struktur Folder

```
UAS-Sistem-Basis-Data/
├─ .venv/
├─ .env
├─ main.py
├─ requirements.txt
└─ recipes_final.txt

```

- `recipes_final.txt` → teks mentah berisi resep per baris/paragraf.
- Script otomatis membuat judul 30 karakter pertama tiap resep.

## f. Jalankan Program

```bash
python main.py

```

Alur program:

1. Load dataset (`recipes_final.txt`)
2. Generate embeddings (`all-MiniLM-L6-v2`)
3. Simpan ke Qdrant (vector DB)
4. Query → cari resep mirip berdasarkan teks pertanyaan
5. Kirim hasil ke Gemini → tampilkan jawaban

Contoh input di CLI:

```
apa resep membuat nasi goreng?

```

<br/>

# Cara Kerja Singkat

- **Indexing:** potong teks → buat embedding → simpan ke Qdrant.
- **Retrieval:** pertanyaan diubah ke vektor → cari top-3 mirip.
- **Generation:** kirim hasil ke Gemini (`gemini-2.0-flash`) → hasil jawaban ditampilkan.

<br/>

# Troubleshooting (FAQ)

### A. `Bind for 0.0.0.0:6333 failed: port is already allocated`

→ Port Qdrant sudah dipakai. Jalankan:

```bash
docker ps
docker stop <container_id>
docker run -d -p 6333:6333 qdrant/qdrant

```

### B. `RuntimeError: GEMINI_API_KEY belum diset`

Pastikan `.env` ada dan ter-load:

- File `.env` berisi `GEMINI_API_KEY=...`
- Di awal script ada `from dotenv import load_dotenv` dan `load_dotenv()`
- Jalankan ulang `python main.py`

### C. `KeyError: 'directions'`

Itu muncul kalau file dibaca sebagai CSV.

Sudah diperbaiki — file dibaca sebagai teks mentah:

```python
with open("recipes_final.txt", "r", encoding="utf-8") as f:
    raw_text = f.read()
texts = [t.strip() for t in raw_text.split("\n") if t.strip()]

```

### D. `AssertionError: Unknown arguments: ['query_vector']`

Gunakan `client.search(..., query_vector=...)` agar lintas-versi Qdrant SDK tetap aman.

### E. `ImportError: cannot import name 'QueryPoints'`

Versi `qdrant-client` belum mendukung `QueryPoints`.

Solusi: pakai `client.search(...)` atau update:

```bash
pip install -U qdrant-client

```

### F. `Gemini 404 / model not found`

- Kalau pakai REST v1beta → `gemini-2.0-flash` ✅
- Kalau pakai `google-generativeai` (v1) → pakai `models/gemini-1.5-flash` dan **hapus** `api_endpoint`.

### G. `ModuleNotFoundError: No module named 'qdrant_client'`

Error ini terjadi kalau `.venv` belum aktif.

Solusi:

1. **Aktifkan venv:**
    
    ```bash
    source .venv/bin/activate
    
    ```
    
    (Windows:)
    
    ```bash
    .venv\Scripts\Activate.ps1
    
    ```
    
2. **Pastikan dependensi sudah diinstall:**
    
    ```bash
    pip install -r requirements.txt
    
    ```
    
3. **Cek Python path:**
    
    ```bash
    which python
    
    ```
    
    Harus mengarah ke `.venv/bin/python`, bukan `/usr/bin/python`.
    

> Kalau tetap error, buat ulang venv:
> 
> 
> ```bash
> python3 -m venv .venv
> source .venv/bin/activate
> pip install -r requirements.txt
> 
> ```
> 

<br/>

# Catatan

- **Vector DB:** Qdrant (COSINE, dimensi 384)
- **Embedding:** `all-MiniLM-L6-v2`
- **LLM:** Gemini 2.0 Flash (v1beta)
- **Top-K retrieval:** 3 dokumen
- **Keamanan:** API key lewat `.env`
- **Repeatability:** Retrieval deterministik, generation non-deterministik.
