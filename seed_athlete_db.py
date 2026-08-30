import os
import chromadb
from chromadb.utils import embedding_functions

# 1. Setup the localized runbooks source directory
RUNBOOKS_DIR = "athlete_runbooks"
CHROMA_DB_PATH = "athlete_chroma_db"

print("[Seeder] Initializing local ChromaDB vector client...")
# Connect to a persistent local directory for saving embeddings
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# 2. Local embedding model — NOT Ollama anymore. See the matching
# comment in trainers/nutrition_trainer.py: this must use the exact
# same embedding function as that file, or queries against this
# collection stop making sense. DefaultEmbeddingFunction downloads
# a small (~80MB) model once and runs on CPU, no server needed.
embedding_fn = embedding_functions.DefaultEmbeddingFunction()

# 3. Create or reset the athletic collection
try:
    chroma_client.delete_collection(name="athlete_knowledge_base")
    print("[Seeder] Cleared previous collection.")
except Exception:
    pass

collection = chroma_client.create_collection(
    name="athlete_knowledge_base",
    embedding_function=embedding_fn
)

# 4. Read documents, extract contents, and load them into ChromaDB
print(f"[Seeder] Scanning '{RUNBOOKS_DIR}' for markdown manuals...")
documents = []
metadatas = []
ids = []

if not os.path.exists(RUNBOOKS_DIR):
    os.makedirs(RUNBOOKS_DIR)
    print(f"[Seeder] Created missing directory: {RUNBOOKS_DIR}. Add your .md files and re-run.")

file_idx = 1
for filename in os.listdir(RUNBOOKS_DIR):
    if filename.endswith(".md"):
        file_path = os.path.join(RUNBOOKS_DIR, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            documents.append(content)
            metadatas.append({"source": filename})
            ids.append(f"runbook_doc_{file_idx}")
            print(f"[Seeder] Processed and queued: {filename}")
            file_idx += 1

# 5. Commit to database if files exist
if documents:
    print("[Seeder] Computing local embeddings (CPU, no external calls)...")
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    print(f"🎉 Success! Vector database successfully seeded with {len(documents)} high-performance manuals.")
else:
    print("⚠️ No markdown (.md) documents found to process. Please check your folder contents.")