# Verba Codebase Guide

## Overview

**Verba: The Golden RAGtriever** is an open-source Retrieval-Augmented Generation (RAG) application built by Weaviate. It provides a complete, user-friendly interface for importing documents, chunking them, embedding them into a vector database, and querying them using various LLM providers.

## What Problem Does Verba Solve?

Verba solves the challenge of building production-ready RAG applications by providing:

1. **End-to-end RAG pipeline** - From document ingestion to answer generation
2. **Flexibility** - Support for multiple LLM providers (OpenAI, Anthropic, Cohere, Ollama, etc.)
3. **Customization** - Pluggable components for reading, chunking, embedding, retrieving, and generating
4. **User-friendly interface** - Web-based UI for non-technical users
5. **Local or cloud deployment** - Works with local models (Ollama) or cloud services

## Architecture Overview

Verba follows a modular, component-based architecture with these main layers:

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                    │
│              React Components + TypeScript               │
└─────────────────────────────────────────────────────────┘
                            ↓ HTTP/WebSocket
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Server Layer                    │
│              REST API + WebSocket Endpoints              │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    VerbaManager                          │
│           Orchestrates all RAG components                │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│              Component Managers (5 types)                │
│  Reader → Chunker → Embedder → Retriever → Generator    │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│              Weaviate Vector Database                    │
│         Stores documents, chunks, and vectors            │
└─────────────────────────────────────────────────────────┘
```

## Core Components

### 1. **VerbaManager** (`verba_manager.py`)

The central orchestrator that manages all components and coordinates the RAG pipeline.

**Key Responsibilities:**
- Manages component lifecycle (Reader, Chunker, Embedder, Retriever, Generator)
- Handles document import workflow
- Coordinates RAG configuration
- Manages Weaviate connections
- Processes queries and generates responses

**Key Methods:**
- `import_document()` - Orchestrates the full document ingestion pipeline
- `retrieve_chunks()` - Retrieves relevant chunks for a query
- `generate_stream_answer()` - Streams LLM responses
- `create_config()` - Builds RAG configuration from available components

### 2. **Component System** (`components/`)

Verba uses a plugin-based component system with 5 types of components:

#### **Reader Components** (`components/reader/`)
- **Purpose**: Import and parse various file formats
- **Supported formats**: PDF, DOCX, CSV, XLSX, TXT, Markdown, Code files, URLs
- **Special readers**: 
  - UnstructuredIO for complex documents
  - GitHub/GitLab for repository ingestion
  - AssemblyAI for audio transcription
  - Firecrawl for web scraping

#### **Chunker Components** (`components/chunking/`)
- **Purpose**: Split documents into manageable pieces for embedding
- **Strategies**:
  - Token-based chunking (using spaCy)
  - Sentence-based chunking
  - Semantic chunking (groups semantically similar sentences)
  - Recursive chunking
  - Format-specific chunkers (HTML, Markdown, Code, JSON)

#### **Embedder Components** (`components/embedding/`)
- **Purpose**: Convert text chunks into vector embeddings
- **Providers**:
  - OpenAI (text-embedding-3-small, etc.)
  - Cohere
  - HuggingFace/SentenceTransformers (local)
  - Ollama (local)
  - VoyageAI
  - Upstage
  - Weaviate Embedding Service

#### **Retriever Components** (`components/retriever/`)
- **Purpose**: Find relevant chunks for a given query
- **Methods**:
  - Hybrid search (semantic + keyword)
  - Pure vector search
  - Filtering by labels and document UUIDs
  - Configurable result limits

#### **Generator Components** (`components/generation/`)
- **Purpose**: Generate natural language responses using LLMs
- **Providers**:
  - OpenAI (GPT-3.5, GPT-4, etc.)
  - Anthropic (Claude)
  - Cohere (Command R+)
  - Ollama (Llama3, Mistral, etc.)
  - Groq (LPU inference)
  - Novita AI
  - Upstage

### 3. **Component Interface** (`components/interfaces.py`)

Defines base classes that all components must implement:

```python
class VerbaComponent:
    - name: Component identifier
    - requires_env: Required environment variables
    - requires_library: Required Python libraries
    - description: Human-readable description
    - config: Configuration parameters
    - type: Component type
```

Each component type extends `VerbaComponent` with specific methods:
- `Reader.load()` - Load documents
- `Chunker.chunk()` - Split documents
- `Embedding.vectorize()` - Create embeddings
- `Retriever.retrieve()` - Find relevant chunks
- `Generator.generate_stream()` - Generate responses

### 4. **Document Model** (`components/document.py`)

Represents a document in Verba's system:

```python
Document:
    - title: Document name
    - content: Full text content
    - chunks: List of Chunk objects
    - extension: File type
    - fileSize: Size in bytes
    - labels: Tags for filtering
    - source: Origin URL or path
    - meta: Internal metadata
    - metadata: User-facing metadata
```

### 5. **FastAPI Server** (`server/api.py`)

Serves the application with REST and WebSocket endpoints:

**Key Endpoints:**
- `/api/connect` - Connect to Weaviate instance
- `/api/query` - Query documents and retrieve chunks
- `/ws/generate_stream` - Stream LLM responses (WebSocket)
- `/ws/import_files` - Import documents (WebSocket)
- `/api/get_all_documents` - List all documents
- `/api/delete_document` - Remove documents
- `/api/set_rag_config` - Update RAG configuration
- `/api/reset` - Reset database

**Security:**
- Same-origin policy enforcement
- CORS middleware
- Production mode restrictions

### 6. **Weaviate Manager** (`components/managers.py`)

Handles all interactions with the Weaviate vector database:

**Key Operations:**
- Create and manage collections (schemas)
- Import documents and chunks
- Vector search and hybrid search
- Metadata management
- Configuration persistence
- Suggestion autocomplete

### 7. **Client Manager** (`verba_manager.py`)

Manages multiple client connections efficiently:

**Features:**
- Connection pooling and reuse
- Credential hashing for security
- Automatic cleanup of stale connections
- Thread-safe operations with asyncio locks

## Data Flow

### Document Import Pipeline

```
1. User uploads file → Frontend
2. File sent via WebSocket → FastAPI Server
3. BatchManager assembles file chunks
4. Reader loads and parses file → Document object
5. Chunker splits document → Document with Chunks
6. Embedder vectorizes chunks → Document with embedded Chunks
7. WeaviateManager imports to database
8. Status updates sent back via WebSocket
```

### Query Pipeline (RAG)

```
1. User enters query → Frontend
2. Query sent to /api/query → FastAPI Server
3. VerbaManager.retrieve_chunks():
   a. Embedder vectorizes query
   b. Retriever searches Weaviate
   c. Returns relevant chunks + context
4. Frontend displays chunks
5. User triggers generation → WebSocket
6. VerbaManager.generate_stream_answer():
   a. Formats prompt with context
   b. Generator streams LLM response
   c. Tokens sent back via WebSocket
7. Frontend displays streaming answer
```

## Frontend Architecture (`frontend/`)

Built with Next.js, React, and TypeScript:

**Main Views:**
- **Login/Getting Started** - Deployment selection
- **Chat Interface** - Query and conversation UI
- **Document Explorer** - Browse and manage documents
- **Ingestion View** - Upload and configure documents
- **Settings** - Configure RAG components

**Key Features:**
- Real-time streaming responses
- 3D vector visualization
- Document chunk viewer
- Configuration management
- Theme customization

## Configuration System

Verba uses a hierarchical configuration system:

### RAG Configuration
Stored in Weaviate with UUID `e0adcc12-9bad-4588-8a1e-bab0af6ed485`

Contains settings for all 5 component types:
```json
{
  "Reader": { "selected": "SimpleReader", "components": {...} },
  "Chunker": { "selected": "TokenChunker", "components": {...} },
  "Embedder": { "selected": "OpenAIEmbedder", "components": {...} },
  "Retriever": { "selected": "HybridRetriever", "components": {...} },
  "Generator": { "selected": "GPT4Generator", "components": {...} }
}
```

### Theme Configuration
Stored with UUID `baab38a7-cb51-4108-acd8-6edeca222820`

### User Configuration
Stored with UUID `f53f7738-08be-4d5a-b003-13eb4bf03ac7`

## Deployment Options

### 1. **Local Deployment**
- Uses Weaviate Embedded (runs in-process)
- Suitable for development and testing
- Not supported on Windows

### 2. **Docker Deployment**
- Separate Weaviate container
- Defined in `docker-compose.yml`
- Production-ready

### 3. **Cloud Deployment (WCS)**
- Connects to Weaviate Cloud Services
- Scalable and managed
- Requires API credentials

### 4. **Custom Deployment**
- User-specified Weaviate instance
- Flexible for existing infrastructure

## Environment Variables

Verba supports extensive configuration via environment variables:

**Database:**
- `WEAVIATE_URL_VERBA` - Weaviate instance URL
- `WEAVIATE_API_KEY_VERBA` - Weaviate API key

**LLM Providers:**
- `OPENAI_API_KEY` - OpenAI access
- `ANTHROPIC_API_KEY` - Anthropic/Claude access
- `COHERE_API_KEY` - Cohere access
- `GROQ_API_KEY` - Groq access
- `OLLAMA_URL` - Local Ollama instance

**Data Ingestion:**
- `UNSTRUCTURED_API_KEY` - UnstructuredIO access
- `ASSEMBLYAI_API_KEY` - Audio transcription
- `GITHUB_TOKEN` - GitHub repository access
- `FIRECRAWL_API_KEY` - Web scraping

**System:**
- `DEFAULT_DEPLOYMENT` - Default deployment mode
- `VERBA_PRODUCTION` - Production mode flag
- `SYSTEM_MESSAGE_PROMPT` - Custom system prompt

## Key Technologies

- **Backend**: Python 3.10-3.12, FastAPI, asyncio
- **Frontend**: Next.js, React, TypeScript, TailwindCSS
- **Database**: Weaviate (vector database)
- **NLP**: spaCy, LangChain, sentence-transformers
- **Deployment**: Docker, pip package

## Package Structure

```
goldenverba/
├── components/
│   ├── chunking/        # Chunking strategies
│   ├── embedding/       # Embedding providers
│   ├── generation/      # LLM generators
│   ├── reader/          # File readers
│   ├── retriever/       # Search strategies
│   ├── chunk.py         # Chunk model
│   ├── document.py      # Document model
│   ├── interfaces.py    # Base classes
│   ├── managers.py      # Component managers
│   └── types.py         # Type definitions
├── server/
│   ├── frontend/        # Built Next.js app
│   ├── api.py           # FastAPI endpoints
│   ├── cli.py           # CLI interface
│   ├── helpers.py       # Utilities
│   └── types.py         # Request/response models
└── verba_manager.py     # Main orchestrator
```

## CLI Usage

```bash
# Install
pip install goldenverba

# Start server
verba start

# With custom port/host
verba start --port 8080 --host 0.0.0.0
```

## Testing

Test files located in `goldenverba/tests/`:
- Document model tests
- Component integration tests
- API endpoint tests

## Extension Points

To add new functionality:

1. **New File Format**: Create a Reader subclass
2. **New Chunking Strategy**: Create a Chunker subclass
3. **New Embedding Provider**: Create an Embedding subclass
4. **New LLM Provider**: Create a Generator subclass
5. **New Retrieval Method**: Create a Retriever subclass

Each component automatically registers and appears in the UI.

## Performance Considerations

- **Async/await**: All I/O operations are asynchronous
- **Batch processing**: Documents processed in parallel
- **Connection pooling**: Reuses Weaviate connections
- **Streaming**: LLM responses streamed for better UX
- **Chunking**: Configurable chunk sizes for memory efficiency

## Security Features

- Same-origin policy enforcement
- Environment variable for sensitive data
- Production mode restrictions
- Credential hashing
- CORS configuration

## Limitations & Known Issues

- Weaviate Embedded not supported on Windows
- Configuration validation required for version compatibility
- Some features marked as "out of scope" (Agentic RAG, Graph RAG)
- Multi-user collaboration not implemented

## Community & Contribution

- Open-source under BSD License
- Community-driven development
- Contributions welcome via GitHub
- Weaviate Community Forum for support

---

## Summary

Verba is a comprehensive, production-ready RAG application that abstracts away the complexity of building retrieval-augmented generation systems. It provides a flexible, modular architecture that supports multiple LLM providers, embedding models, and deployment options, all wrapped in an intuitive web interface. The codebase is well-structured for extension and customization while providing sensible defaults for quick deployment.
