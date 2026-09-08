import chromadb
import pandas
from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document

from app.config import settings


class RAGEngine:
    """
    RAG engine backed by ChromaDB and orchestrated by LangChain.

    Public API (unchanged from the SQLite-based version):
        - add_resolved_incident(number, short_description, resolution, resolved_by)
        - search_similar_incidents(query, top_k=2) -> list of dicts
        - get_all_resolved_incidents() -> list of dicts (used by /api/history)
        - seed_historical_incidents(seed_list) -> bulk-loads historical KB

    Storage: ChromaDB collection at settings.CHROMA_PERSIST_DIR / settings.CHROMA_COLLECTION_NAME.
    Embeddings: settings.OLLAMA_EMBED_MODEL via langchain_community.embeddings.OllamaEmbeddings.
    """

    def __init__(self):
        # 1. LangChain embedding function wrapping the local Ollama model
        self.embeddings = OllamaEmbeddings(
            model=settings.OLLAMA_EMBED_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
        )

        # 2. Persistent ChromaDB client on disk
        self.chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        # 3. LangChain Chroma vector store bound to the named collection
        self.vectorstore = Chroma(
            client=self.chroma_client,
            collection_name=settings.CHROMA_COLLECTION_NAME,
            embedding_function=self.embeddings,
        )

    def get_related_inc(self, query: str):
        """
        Return the most relevant resolved incident for the given query.

        Uses LangChain Chroma's similarity_search_with_score which returns
        raw distance scores (lower distance = higher similarity).

        Returns:
            tuple[Document, float] | None:
                (matched_document, distance_score) or None when there are
                no documents in the collection.
        """
        results = self.vectorstore.similarity_search_with_score(query, k=1)
        if not results:
            return None
        doc, score = results[0]
        print(f"[RAG] Best match: {doc.metadata.get('inc_number')} | distance score: {score}")
        return doc, score



    def seed_historical_incidents(self) -> None:
        """
        Bulk-loads the historical seed list into ChromaDB on first startup.
        Skips if the collection already has documents (idempotent across restarts).
        """
        existing = self.chroma_client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME
        )
        if existing.count() > 0:
            print(
                f"ChromaDB collection already has {existing.count()} docs; "
                "skipping seed."
            )
            return

        print("Reading excel file...")
        df = pandas.read_excel(settings.RESOLVED_INC_EXCEL_FILE)
        record_count = df["INC Number"].count()
        print(
            f"Seeding {record_count} historical resolved incidents "
            "into ChromaDB..."
        )
        documents = []
        for index,row in df.iterrows():
            row_text = f'''
            Description: {row["Description"]}
            Root Cause: {row["Root Cause"]}
            Assignment Group: {row['Assignment Group']}
            '''
            metadata = {
                "row_index":index,
                "inc_number":row['INC Number']
            }
            documents.append(
                Document(page_content=row_text,metadata=metadata,id=row['INC Number'])
            )
        self.vectorstore.add_documents(documents)
        print("Historical incidents seeded into ChromaDB successfully.")


rag_engine = RAGEngine()
