# System Architecture & Flow Diagrams

## 1. Complete RAG Flow - Step by Step

```mermaid
flowchart TD
    Start([User asks question]) --> API[FastAPI: /ask endpoint - routes/api.py]
    
    API --> Handler[query_handler.py - handle_question]
    
    Handler --> GenEmbed[embeddings.py - generate_embedding]
    GenEmbed --> QEmbed[Query Vector - 384/768 dimensions]
    
    QEmbed --> Search[retrieval.py - retrieve_relevant_chunks]
    
    Search --> Qdrant[(Qdrant - search_vectors)]
    Qdrant --> VecResults[Top-K similar vectors with scores]
    
    VecResults --> PG[(PostgreSQL - get chunks by IDs)]
    PG --> Chunks[Full chunk objects with metadata]
    
    Chunks --> Format[retrieval.py - format_context_for_llm]
    Format --> Context[Formatted context string]
    
    Context --> LLM[query_handler.py - generate_answer_with_llm]
    LLM --> OpenRouter[OpenRouter API - LLM inference]
    OpenRouter --> Answer[Generated answer]
    
    Answer --> Log[Save to query_logs table]
    Log --> Response([Return JSON response])
    
    style Start fill:#e1f5e1
    style Response fill:#e1f5e1
    style Qdrant fill:#ffebcc
    style PG fill:#ffebcc
    style OpenRouter fill:#cce5ff
```

## 2. Document Indexing Flow

```mermaid
flowchart TD
    Upload([POST /documents]) --> API[routes/api.py - create_document]
    
    API --> Index[indexing.py - index_document]
    
    Index --> CreateDoc[Create Document record in PostgreSQL]
    CreateDoc --> DocID[Get document.id]
    
    DocID --> Chunk[chunking.py - smart_chunk]
    Chunk --> Chunks[List of text chunks]
    
    Chunks --> Embed[embeddings.py - generate_embeddings_batch]
    Embed --> Vectors[List of embedding vectors]
    
    Vectors --> SaveChunks[Save Chunk records to PostgreSQL]
    SaveChunks --> ChunkIDs[Get chunk.id for each]
    
    ChunkIDs --> Points[Create PointStruct objects - id, vector, payload]
    Points --> Upsert[qdrant_client.py - upsert_vectors]
    Upsert --> QdrantDB[(Store in Qdrant collection)]
    
    QdrantDB --> Complete([Document indexed!])
    
    style Upload fill:#e1f5e1
    style Complete fill:#e1f5e1
    style QdrantDB fill:#ffebcc
```

## 3. Class and Function Relationships

```mermaid
classDiagram
    class FastAPIApp {
        +routes/api.py
        +ask_question()
        +create_document()
        +search()
        +list_documents()
        +get_stats()
    }
    
    class QueryHandler {
        +services/query_handler.py
        +handle_question()
        +generate_answer_with_llm()
        +simple_answer()
    }
    
    class RetrievalService {
        +services/retrieval.py
        +retrieve_relevant_chunks()
        +format_context_for_llm()
        +deduplicate_chunks()
    }
    
    class IndexingService {
        +services/indexing.py
        +index_document()
        +delete_document()
        +reindex_document()
    }
    
    class EmbeddingUtils {
        +utils/embeddings.py
        +generate_embedding()
        +generate_embeddings_batch()
        +get_embedding_model()
    }
    
    class ChunkingUtils {
        +utils/chunking.py
        +smart_chunk()
        +chunk_text()
        +chunk_by_sentences()
    }
    
    class QdrantClient {
        +db/qdrant_client.py
        +search_vectors()
        +upsert_vectors()
        +delete_by_document_id()
        +init_collection()
    }
    
    class PostgresDB {
        +db/postgres.py
        +get_db()
        +init_db()
        +SessionLocal
    }
    
    class SQLAlchemyModels {
        +models/pg_models.py
        +Document
        +Chunk
        +QueryLog
    }
    
    class PydanticModels {
        +models/qdrant_models.py
        +QuestionRequest
        +QuestionResponse
        +DocumentCreate
    }
    
    FastAPIApp --> QueryHandler : calls
    FastAPIApp --> IndexingService : calls
    FastAPIApp --> RetrievalService : calls
    FastAPIApp --> PostgresDB : uses
    
    QueryHandler --> RetrievalService : uses
    QueryHandler --> EmbeddingUtils : uses
    
    RetrievalService --> QdrantClient : uses
    RetrievalService --> PostgresDB : uses
    RetrievalService --> EmbeddingUtils : uses
    
    IndexingService --> ChunkingUtils : uses
    IndexingService --> EmbeddingUtils : uses
    IndexingService --> QdrantClient : uses
    IndexingService --> PostgresDB : uses
    
    FastAPIApp ..> PydanticModels : validates with
    PostgresDB ..> SQLAlchemyModels : defines schema
```

## 4. Database Schema Relationships

```mermaid
erDiagram
    Document ||--o{ Chunk : contains
    Document {
        int id PK
        string title
        text content
        string source
        string doc_type
        datetime created_at
    }
    
    Chunk {
        int id PK
        int document_id FK
        text chunk_text
        int chunk_index
        int chunk_size
        datetime created_at
    }
    
    QueryLog {
        int id PK
        text question
        text answer
        int chunks_retrieved
        float avg_score
        float response_time
        datetime created_at
    }
    
    QdrantVector {
        int id "chunk.id"
        vector embedding "384 or 768 dim"
        json payload
    }
    
    Chunk ||--|| QdrantVector : has_embedding
```

## 5. Detailed RAG Question Flow with Functions

```mermaid
sequenceDiagram
    participant User
    participant API as FastAPI<br/>api.py
    participant Handler as QueryHandler<br/>query_handler.py
    participant Retrieval as RetrievalService<br/>retrieval.py
    participant Embed as EmbeddingUtils<br/>embeddings.py
    participant Qdrant as QdrantClient<br/>qdrant_client.py
    participant PG as PostgreSQL<br/>postgres.py
    participant LLM as OpenRouter API
    
    User->>API: POST /ask {question}
    API->>Handler: handle_question(question)
    
    Handler->>Retrieval: retrieve_relevant_chunks(question)
    Retrieval->>Embed: generate_embedding(question)
    Embed-->>Retrieval: query_vector
    
    Retrieval->>Qdrant: search_vectors(query_vector)
    Qdrant-->>Retrieval: [chunk_ids, scores]
    
    Retrieval->>PG: query(Chunk).filter(id.in_(chunk_ids))
    PG-->>Retrieval: [Chunk objects]
    Retrieval-->>Handler: [(chunk, score), ...]
    
    Handler->>Retrieval: format_context_for_llm(chunks)
    Retrieval-->>Handler: context_string
    
    Handler->>LLM: generate_answer_with_llm(question, context)
    LLM-->>Handler: answer_text
    
    Handler->>PG: Save QueryLog(question, answer, ...)
    Handler-->>API: {answer, chunks, metadata}
    API-->>User: JSON response
```

## 6. Document Indexing Sequence

```mermaid
sequenceDiagram
    participant User
    participant API as FastAPI<br/>api.py
    participant Index as IndexingService<br/>indexing.py
    participant Chunk as ChunkingUtils<br/>chunking.py
    participant Embed as EmbeddingUtils<br/>embeddings.py
    participant PG as PostgreSQL
    participant Qdrant as Qdrant
    
    User->>API: POST /documents {title, content}
    API->>Index: index_document(title, content)
    
    Index->>PG: Create Document record
    PG-->>Index: document.id
    
    Index->>Chunk: smart_chunk(content)
    Chunk-->>Index: [chunk1, chunk2, ...]
    
    Index->>Embed: generate_embeddings_batch([chunks])
    Embed-->>Index: [vector1, vector2, ...]
    
    Index->>PG: Create Chunk records
    PG-->>Index: [chunk.id, ...]
    
    Index->>Qdrant: upsert_vectors([PointStruct(...)])
    Qdrant-->>Index: Success
    
    Index-->>API: document object
    API-->>User: {id, chunk_count, ...}
```

## 7. Component Dependencies

```mermaid
graph TD
    subgraph "API Layer"
        API[routes/api.py]
    end
    
    subgraph "Service Layer"
        QH[query_handler.py]
        Ret[retrieval.py]
        Idx[indexing.py]
    end
    
    subgraph "Utility Layer"
        Emb[embeddings.py]
        Chk[chunking.py]
        Log[logging.py]
    end
    
    subgraph "Database Layer"
        PG[postgres.py]
        QD[qdrant_client.py]
    end
    
    subgraph "Model Layer"
        PGM[pg_models.py]
        QDM[qdrant_models.py]
    end
    
    subgraph "External Services"
        PGDB[(PostgreSQL)]
        QDDB[(Qdrant)]
        OR[OpenRouter API]
        ST[sentence-transformers]
    end
    
    API --> QH
    API --> Ret
    API --> Idx
    
    QH --> Ret
    QH --> Emb
    QH --> OR
    
    Ret --> QD
    Ret --> PG
    Ret --> Emb
    
    Idx --> Chk
    Idx --> Emb
    Idx --> PG
    Idx --> QD
    
    Emb --> ST
    
    PG --> PGDB
    PG --> PGM
    
    QD --> QDDB
    
    API --> QDM
    
    style API fill:#e1f5e1
    style QH fill:#cce5ff
    style Ret fill:#cce5ff
    style Idx fill:#cce5ff
    style Emb fill:#ffe6cc
    style Chk fill:#ffe6cc
    style PG fill:#ffcccc
    style QD fill:#ffcccc
    style PGDB fill:#ffebcc
    style QDDB fill:#ffebcc
    style OR fill:#e6ccff
    style ST fill:#e6ccff
```

## 8. Function Call Hierarchy - Ask Question

```
routes/api.py::ask_question()
│
├─► services/query_handler.py::handle_question()
    │
    ├─► services/retrieval.py::retrieve_relevant_chunks()
    │   │
    │   ├─► utils/embeddings.py::generate_embedding()
    │   │   └─► utils/embeddings.py::get_embedding_model()
    │   │
    │   ├─► db/qdrant_client.py::search_vectors()
    │   │   └─► qdrant_client.search()  [external]
    │   │
    │   └─► db.query(Chunk).filter()  [SQLAlchemy]
    │
    ├─► services/retrieval.py::deduplicate_chunks()
    │
    ├─► services/retrieval.py::format_context_for_llm()
    │
    ├─► services/query_handler.py::generate_answer_with_llm()
    │   └─► requests.post(OpenRouter API)  [external]
    │
    └─► db.add(QueryLog)  [SQLAlchemy]
```

## 9. Function Call Hierarchy - Index Document

```
routes/api.py::create_document()
│
└─► services/indexing.py::index_document()
    │
    ├─► db.add(Document)  [SQLAlchemy]
    │
    ├─► utils/chunking.py::smart_chunk()
    │   ├─► chunking.py::chunk_text()  [if needed]
    │   └─► chunking.py::chunk_by_paragraphs()  [if needed]
    │
    ├─► utils/embeddings.py::generate_embeddings_batch()
    │   ├─► utils/embeddings.py::get_embedding_model()
    │   └─► model.encode()  [sentence-transformers]
    │
    ├─► db.add(Chunk) for each chunk  [SQLAlchemy]
    │
    └─► db/qdrant_client.py::upsert_vectors()
        └─► qdrant_client.upsert()  [external]
```

## 10. Key Function Reference

### API Layer (routes/api.py)
- `ask_question()` - Main RAG endpoint
- `create_document()` - Index new document
- `search()` - Search chunks only
- `list_documents()` - Get all documents
- `get_stats()` - System statistics

### Query Handler (services/query_handler.py)
- `handle_question()` - Complete RAG pipeline
- `generate_answer_with_llm()` - Call OpenRouter
- `simple_answer()` - Direct LLM (no RAG)

### Retrieval (services/retrieval.py)
- `retrieve_relevant_chunks()` - Vector search + fetch
- `format_context_for_llm()` - Format chunks for prompt
- `deduplicate_chunks()` - Remove duplicates
- `search_chunks_by_text()` - Text-based search

### Indexing (services/indexing.py)
- `index_document()` - Full indexing pipeline
- `delete_document()` - Remove document
- `reindex_document()` - Re-process document
- `get_indexing_stats()` - Get statistics

### Embeddings (utils/embeddings.py)
- `generate_embedding()` - Single text embedding
- `generate_embeddings_batch()` - Batch processing
- `get_embedding_model()` - Model singleton
- `cosine_similarity()` - Similarity calculation

### Chunking (utils/chunking.py)
- `smart_chunk()` - Intelligent chunking
- `chunk_text()` - Character-based
- `chunk_text_by_sentences()` - Sentence-based
- `chunk_text_by_paragraphs()` - Paragraph-based

### Qdrant Client (db/qdrant_client.py)
- `init_collection()` - Create collection
- `search_vectors()` - Similarity search
- `upsert_vectors()` - Insert/update vectors
- `delete_by_document_id()` - Delete vectors

### PostgreSQL (db/postgres.py)
- `get_db()` - Database session
- `init_db()` - Create tables
- `SessionLocal` - Session factory

## 11. Data Flow Summary

```
INPUT (Question)
      ↓
[Embedding Generation] → Vector (384/768 dims)
      ↓
[Vector Search] → Qdrant finds similar chunks
      ↓
[Metadata Fetch] → PostgreSQL gets full chunks
      ↓
[Context Formation] → Format chunks into prompt
      ↓
[LLM Generation] → OpenRouter generates answer
      ↓
OUTPUT (Answer + Sources)
```

## 12. Module Interaction Map

```
┌─────────────────────────────────────────────────────┐
│                    FastAPI App                       │
│                    (main.py)                        │
└────────────────┬───────────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    ▼                         ▼
┌─────────┐              ┌──────────┐
│   API   │              │   DB     │
│ Routes  │◄────────────►│  Init    │
└────┬────┘              └──────────┘
     │
     ├──► Query Handler ──┬──► Retrieval ──┬──► Qdrant Client
     │                    │                 └──► PostgreSQL
     │                    │
     │                    └──► Embeddings ──► sentence-transformers
     │
     └──► Indexing ───────┬──► Chunking
                          ├──► Embeddings
                          ├──► PostgreSQL
                          └──► Qdrant Client
```