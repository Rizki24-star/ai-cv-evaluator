import asyncio
import json
import logging
import sys

from sqlalchemy.orm import Session

from src.models.qdrant import ChunkMetadata
from src.repository import role_repository, document_reference_repository, category_repository
from src.databases.postgres.database import sessionLocal
from src.services.gemini_service import get_gemini_service
from src.services.qdrant_service import get_qdrant_service
from src.config import get_settings

# Configure logging to show INFO level logs to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

async def ingest_data(db: Session, job_role_name: str):
    gemini = get_gemini_service()
    qdrant = get_qdrant_service()
    # settings = get_settings()
    qdrant.create_collections(db)

    role = role_repository.find_role_by_name(db, job_role_name)
    docs_ref = document_reference_repository.find_docs_by_role_id_and_titles(db, role.id, ['Case Study Brief', 'Job Description'])
    logging.info(
        f"Found {len(docs_ref)} reference documents for role: {job_role_name}"
    )

    if not role:
        logging.warning(f"Role not found: {job_role_name}")
        return
    logging.info(f"Found role: {role}")
    result_chunks = []
    for doc_ref in docs_ref:
        logging.info(f"Processing document: {doc_ref}")
        chunks = flatten_json_to_chunks(
            doc_ref.content,
            job_role=role.name,
            title=role.name,
            prefix=getattr(doc_ref, 'title', '')
        )
        result_chunks.extend(chunks)

        # Get collection name by category
        collection_name: str = doc_ref.category.collection_name

        # Generate embeddings for the current document's chunks (list of dicts) by extracting text fields
        texts = [c.get('text', '') if isinstance(c, dict) else str(c) for c in chunks]
        try:
            embeddings = await gemini.generate_embeddings(texts)
        except Exception as e:
            logging.error(f"Embedding generation error: {e}")
            continue
        logging.info(f"Generated {len(embeddings)} embeddings for {len(chunks)} chunks")

        # Ensure embeddings align with chunks
        if len(embeddings) != len(chunks):
            min_len = min(len(embeddings), len(chunks))
            logging.warning(f"Embeddings/chunks length mismatch: {len(embeddings)} vs {len(chunks)}. Truncating to {min_len}.")
            chunks = chunks[:min_len]
            embeddings = embeddings[:min_len]

        chunk_models = [
            ChunkMetadata(
                source=collection_name,
                content=c.get("text", ""),
                chunk_index=c.get("order_index", 0),
                section=c.get("path", None),
                category=None,
            ) for c in chunks
        ]

        logging.info(f"Ingesting to Qdrant collection: {collection_name}")


        count = qdrant.ingest_documents(
            collection_name=collection_name,
            chunks=chunk_models,
            embeddings=embeddings
        )
        logging.info(f"Successfully ingested {count} chunks into {collection_name}")

    logging.info(f"Result {len(result_chunks)} chunks")

def flatten_json_to_chunks(data, job_role: str, title: str, prefix: "", counter=[0], max_len=1000):
    chunks = []

    def build_path(prefix_val: str, key_part: str) -> str:
        # Ensure job_role appears exactly once at the start of the path
        if not prefix_val:
            # top-level
            return f"{job_role}.{key_part}" if key_part else job_role
        # If prefix already starts with job_role, don't duplicate it
        if prefix_val.startswith(job_role):
            if key_part.startswith("["):
                return f"{prefix_val}{key_part}"
            return f"{prefix_val}.{key_part}"
        # Otherwise, prefix does not include job_role yet
        if key_part.startswith("["):
            return f"{job_role}.{prefix_val}{key_part}"
        return f"{job_role}.{prefix_val}.{key_part}"

    if isinstance(data, dict):
        for k, v in data.items():
            counter[0] += 1
            path = build_path(prefix, k)
            text = f"{path}: {json.dumps(v, ensure_ascii=False)}"
            logging.info(f"Processing: {text}")

            if isinstance(v, str) and len(v) > max_len:
                for idx, i in enumerate(range(0, len(v), max_len)):
                    piece = v[i:i+max_len]
                    sub_path = f"{path}[part_{idx}]"
                    counter[0] += 1
                    chunks.append({
                        "text": f"{sub_path}: {piece}",
                        "path": sub_path,
                        "order_index": counter[0]
                    })
            else:
                chunks.append({
                    "text": text,
                    "path": path,
                    "order_index": counter[0]
                })
                chunks.extend(flatten_json_to_chunks(v, job_role, title, path, counter))
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            counter[0] += 1
            path = build_path(prefix, f"[{idx}]")
            text = f"{path}: {json.dumps(item, ensure_ascii=False)}"
            chunks.append({"text": text, "path": path, "order_index": counter[0]})
            chunks.extend(flatten_json_to_chunks(item, job_role, title, path, counter))
    return chunks

async def main():
    logging.info("Starting database ingestion script")
    db: Session = sessionLocal()
    try:
        roles = role_repository.find_all(db)
        logging.info(f"Found {len(roles)} roles to ingest")
        for role in roles:
            logging.info(f"Ingesting role: {getattr(role, 'name', str(role))}")
            await ingest_data(db, role.name)
        logging.info("Ingestion completed successfully")
    finally:
        db.close()
        logging.info("DB session closed")

if __name__ == "__main__":
    asyncio.run(main())
