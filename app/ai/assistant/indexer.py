import os
import glob
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings


CHROMA_PERSIST_DIR = "ml_data/chroma_db"
COLLECTION_NAME = "ev_network_knowledge_base"


class KnowledgeBaseIndexer:
    """
    RAG Vector Store Manager using ChromaDB.
    Indexes network policy, tariff, technical, and troubleshooting documentation
    into dense vector embeddings for semantic similarity retrieval.
    """

    def __init__(self, persist_dir: str = CHROMA_PERSIST_DIR):
        self.persist_dir = persist_dir
        os.makedirs(self.persist_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        # Ensure knowledge base is indexed
        if self.collection.count() == 0:
            self.index_all_documents()

    def chunk_markdown(self, file_path: str, chunk_size: int = 450, overlap: int = 60) -> List[Dict[str, Any]]:
        """
        Splits markdown document into semantic chunks while tracking section headers.
        """
        filename = os.path.basename(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        sections = content.split("\n## ")
        doc_chunks = []
        doc_title = sections[0].split("\n")[0].replace("#", "").strip()

        for s_idx, sec in enumerate(sections):
            lines = sec.split("\n")
            header = lines[0].strip() if s_idx > 0 else "Overview"
            body = "\n".join(lines[1:] if s_idx > 0 else lines).strip()

            if not body:
                continue

            # Sliding window chunking
            start = 0
            chunk_num = 1
            while start < len(body):
                end = min(start + chunk_size, len(body))
                chunk_text = body[start:end].strip()
                if chunk_text:
                    full_context = f"{doc_title} > {header}:\n{chunk_text}"
                    doc_chunks.append({
                        "id": f"{filename}-{s_idx}-{chunk_num}",
                        "text": full_context,
                        "metadata": {
                            "source_file": filename,
                            "doc_title": doc_title,
                            "section_header": header,
                            "chunk_index": chunk_num,
                        },
                    })
                    chunk_num += 1

                if end == len(body):
                    break
                start = end - overlap

        return doc_chunks

    def index_all_documents(self, docs_dir: str = "docs/knowledge_base") -> int:
        """
        Ingests all Markdown knowledge base documents into ChromaDB.
        """
        md_files = glob.glob(os.path.join(docs_dir, "*.md"))
        if not md_files:
            print(f"Warning: No markdown files found in {docs_dir}")
            return 0

        all_chunks = []
        for file_path in md_files:
            chunks = self.chunk_markdown(file_path)
            all_chunks.extend(chunks)

        if not all_chunks:
            return 0

        # Ingest into ChromaDB
        ids = [c["id"] for c in all_chunks]
        documents = [c["text"] for c in all_chunks]
        metadatas = [c["metadata"] for c in all_chunks]

        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

        print(f"KnowledgeBaseIndexer: Successfully indexed {len(all_chunks)} chunks from {len(md_files)} documents into ChromaDB.")
        return len(all_chunks)

    def search(self, query_text: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Performs semantic vector similarity search using Cosine distance.
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=min(n_results, max(1, self.collection.count())),
        )

        formatted = []
        if results and results.get("documents") and len(results["documents"]) > 0:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
            distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

            for doc, meta, dist in zip(docs, metas, distances):
                # Cosine distance to similarity score
                similarity = round(max(0.0, 1.0 - dist), 3)
                formatted.append({
                    "text": doc,
                    "metadata": meta,
                    "similarity": similarity,
                    "source_file": meta.get("source_file", "knowledge_base.md"),
                    "section_header": meta.get("section_header", "Policy"),
                })

        return formatted


# Global singleton instance
knowledge_indexer = KnowledgeBaseIndexer()

