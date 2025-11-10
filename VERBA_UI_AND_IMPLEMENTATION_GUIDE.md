# Verba UI & Implementation Guide

## Table of Contents
1. [User Interface Overview](#user-interface-overview)
2. [Chat Interface Detailed Guide](#chat-interface-detailed-guide)
3. [Retriever Implementation](#retriever-implementation)
4. [Generator Implementation](#generator-implementation)

---

## User Interface Overview

Verba's UI is built with Next.js, React, and TypeScript, featuring a two-panel layout for chat and document exploration.

### Main Views

1. **Login/Getting Started** - Initial deployment selection
2. **Chat View** - Main RAG interface (two-panel layout)
3. **Document Explorer** - Browse and manage documents
4. **Ingestion View** - Upload and configure documents
5. **Settings** - System configuration

---

## Chat Interface Detailed Guide

### Layout Structure

The Chat View (`ChatView.tsx`) uses a responsive two-panel design:

```
┌─────────────────────────────────────────────────────────┐
│                    Chat Interface                        │
│                     (Left Panel)                         │
│  - Query input                                           │
│  - Conversation history                                  │
│  - Configuration panel                                   │
│  - Filters and labels                                    │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                  Document Explorer                       │
│                    (Right Panel)                         │
│  - Retrieved documents                                   │
│  - Chunk viewer with highlighting                        │
│  - Document metadata                                     │
│  - Vector visualization                                  │
└─────────────────────────────────────────────────────────┘
```

**Responsive Behavior:**
- Desktop: Both panels visible side-by-side
- Mobile: Panels stack, showing one at a time
- When document selected: Right panel takes focus on mobile

### Left Panel: Chat Interface Components

#### 1. **Header Section**
Located at the top of the chat interface:

**Components:**
- **Info Icon** - Tooltip explaining RAG functionality
- **Chat Button** - Switch to chat view (default)
- **Config Button** - Switch to configuration view (hidden in Demo mode)

**Code Location:** `ChatInterface.tsx` lines 300-330

#### 2. **Filter Bar** (Sticky at top when scrolling)

**Label Filter Dropdown:**
- **Button:** "Label" with plus icon
- **Function:** Filter documents by metadata labels
- **Interaction:** 
  - Click to open dropdown
  - Select label to add to active filters
  - Multiple labels can be selected (AND logic)

**Active Filters Display:**
- Shows selected labels as removable chips (primary color)
- Shows selected documents as removable chips (secondary color)
- **Clear Button:** Removes all filters at once

**Code Location:** `ChatInterface.tsx` lines 340-410

#### 3. **Message Display Area**

**Message Types:**

1. **System Messages** (Left-aligned, gray background)
   - Initial greeting message
   - AI-generated responses
   - Shows "cached" badge if response was cached
   - Displays distance metric for cached responses

2. **User Messages** (Right-aligned, primary color)
   - User queries
   - Displayed in chat bubbles

3. **Retrieval Messages** (Full-width, special formatting)
   - Shows retrieved documents
   - Displays document cards with:
     - Document title
     - Relevance score
     - Number of chunks
     - Metadata
   - Click to view in right panel

4. **Error Messages** (Red background)
   - API errors
   - Connection issues
   - No results found

**Loading States:**
- "Retrieving..." - Fetching chunks from database
- "Generating..." - LLM generating response
- Animated dots indicator
- Cancel button to stop generation

**Code Location:** `ChatInterface.tsx` lines 420-480

#### 4. **Input Section** (Bottom, fixed)

**Main Textarea:**
- Auto-expanding (40px min, 150px max)
- Placeholder shows document count
- Enter to send (Shift+Enter for new line)
- Handles IME composition (for Asian languages)

**Autocomplete Suggestions:**
- Appears below input after typing
- Shows up to 3 suggestions
- Highlights matching text
- Click to use suggestion
- Triggered every 3 characters

**Action Buttons:**
- **Send Button** (Paper plane icon)
  - Sends current message
  - Disabled when fetching or input empty
  - Primary color when active

- **Refresh Button** (Circular arrow icon)
  - Clears conversation
  - Resets to initial state
  - Clears selected documents and filters

**Connection Status:**
- Shows "Reconnecting..." if WebSocket disconnected
- Displays connection icon and spinner
- Auto-reconnects on failure

**Code Location:** `ChatInterface.tsx` lines 550-650

### Configuration Panel

Accessible via "Config" button (hidden in Demo mode).

#### Component Sections:

**1. Embedder Configuration**
- **Model Selection:** Dropdown of available embedding models
- **API Key Input:** If not set in environment
- **URL Configuration:** Custom endpoint (if applicable)
- Shows availability status (green checkmark or red X)

**2. Generator Configuration**
- **Model Selection:** Choose LLM (GPT-4, Claude, etc.)
- **System Message:** Customize AI behavior
  - Large textarea for prompt engineering
  - Default: RAG-focused instructions
- **API Key Input:** Provider-specific key
- **URL Configuration:** Custom endpoint support

**3. Retriever Configuration**
- **Search Mode:** Hybrid Search (semantic + keyword)
- **Limit Mode:** 
  - "Autocut" - Automatic relevance threshold
  - "Fixed" - Set number of chunks
- **Limit/Sensitivity:** Numeric value for above setting
- **Chunk Window:** Number of surrounding chunks to include (0-10)
- **Threshold:** Minimum score to apply window technique (0-100)

**Save/Reset Buttons:**
- **Save Config:** Persists changes to Weaviate
- **Reset:** Reverts to last saved configuration
- Both disabled in Demo mode

**Code Location:** `ChatConfig.tsx`

---

## Right Panel: Document Explorer

### Features:

1. **Document List View**
   - Shows all retrieved documents
   - Sorted by relevance score
   - Click to view details

2. **Chunk Viewer**
   - Displays document chunks
   - Highlights retrieved chunks
   - Shows surrounding context
   - Pagination controls

3. **Metadata Display**
   - Document properties
   - Labels and tags
   - Source information

4. **Vector Visualization** (3D)
   - Interactive 3D scatter plot
   - Shows chunk embeddings
   - Color-coded by relevance

---

## Retriever Implementation

### WindowRetriever Class

**File:** `goldenverba/components/retriever/WindowRetriever.py`

#### Purpose
Retrieves relevant chunks from Weaviate and includes surrounding context based on a configurable window size.

#### Configuration Parameters

```python
{
    "Search Mode": "Hybrid Search",  # Search type
    "Limit Mode": "Autocut",         # How to limit results
    "Limit/Sensitivity": 1,          # Autocut sensitivity or fixed limit
    "Chunk Window": 1,               # Surrounding chunks to include
    "Threshold": 80                  # Score threshold (0-100)
}
```

#### How It Works

**Step 1: Initial Retrieval**
```python
async def retrieve(self, client, query, vector, config, ...):
    # Perform hybrid search (semantic + keyword)
    chunks = await weaviate_manager.hybrid_chunks(
        client, embedder, query, vector, 
        limit_mode, limit, labels, document_uuids
    )
```

**Step 2: Group by Document**
```python
# Organize chunks by parent document
doc_map = {}
for chunk in chunks:
    if chunk.properties["doc_uuid"] not in doc_map:
        # Create document entry
        doc_map[doc_uuid] = {
            "title": document["title"],
            "chunks": [],
            "score": 0,
            "metadata": document["metadata"]
        }
    # Add chunk and accumulate score
    doc_map[doc_uuid]["chunks"].append(chunk_data)
    doc_map[doc_uuid]["score"] += chunk.metadata.score
```

**Step 3: Score Normalization**
```python
# Normalize scores between 0 and 1
def normalize_value(value, max_value, min_value):
    return (value - min_value) / (max_value - min_value)

normalized_score = normalize_value(
    chunk["score"], max_score, min_score
)
```

**Step 4: Window Expansion**
```python
# For chunks above threshold, get surrounding chunks
if window_threshold <= normalized_score:
    # Generate list of surrounding chunk IDs
    additional_chunk_ids = generate_window_list(
        chunk["chunk_id"], window
    )
    # Fetch additional chunks from database
    additional_chunks = await weaviate_manager.get_chunk_by_ids(
        client, embedder, doc_uuid, unique_chunk_ids
    )
```

**Step 5: Context Assembly**
```python
def combine_context(self, documents: list[dict]) -> str:
    context = ""
    for document in documents:
        context += f"Document Title: {document['title']}\n"
        context += f"Document Metadata: {document['metadata']}\n"
        for chunk in document["chunks"]:
            context += f"Chunk: {chunk['chunk_id']+1}\n"
            if chunk["score"] > 0:
                context += f"High Relevancy: {chunk['score']:.2f}\n"
            context += f"{chunk['content']}\n"
    return context
```

#### Return Values

**Documents Array** (for UI display):
```python
[{
    "title": "Document Title",
    "uuid": "doc-uuid",
    "score": 0.95,
    "metadata": "Additional info",
    "chunks": [{
        "uuid": "chunk-uuid",
        "score": 0.98,
        "chunk_id": 5,
        "embedder": "OpenAI"
    }]
}]
```

**Context String** (for LLM):
```
Document Title: Example Document
Document Metadata: Source: example.pdf
Chunk: 5
High Relevancy: 0.98
[Chunk content here...]

Chunk: 6
[Surrounding context...]
```

#### Key Features

1. **Hybrid Search:** Combines semantic similarity with keyword matching
2. **Autocut:** Automatically determines optimal number of chunks
3. **Window Technique:** Includes surrounding chunks for better context
4. **Score-based Filtering:** Only applies window to high-relevance chunks
5. **Document Grouping:** Organizes chunks by source document

---

## Generator Implementation

Generators convert retrieved context into natural language responses using LLMs.

### Base Generator Interface

**File:** `goldenverba/components/interfaces.py`

```python
class Generator(VerbaComponent):
    def __init__(self):
        self.context_window = 5000  # Max tokens
        self.config["System Message"] = InputConfig(
            type="textarea",
            value="You are Verba, a chatbot for RAG...",
            description="System Message"
        )
    
    async def generate_stream(
        self, queries, context, conversation
    ):
        # Must be implemented by subclass
        # Yields: {"message": token, "finish_reason": "stop"|None}
        
    def prepare_messages(
        self, queries, context, conversation
    ):
        # Formats messages for specific LLM API
```

### OpenAI Generator Implementation

**File:** `goldenverba/components/generation/OpenAIGenerator.py`

#### Configuration

```python
def __init__(self):
    self.name = "OpenAI"
    self.context_window = 10000
    
    # Fetch available models from API
    models = self.get_models(api_key, base_url)
    
    self.config["Model"] = InputConfig(
        type="dropdown",
        value="gpt-4o",
        values=models  # ["gpt-4o", "gpt-3.5-turbo", ...]
    )
    
    # Optional configs if not in environment
    if not os.getenv("OPENAI_API_KEY"):
        self.config["API Key"] = InputConfig(...)
    if not os.getenv("OPENAI_BASE_URL"):
        self.config["URL"] = InputConfig(...)
```

#### Streaming Generation

```python
async def generate_stream(
    self, config, query, context, conversation
):
    # Extract configuration
    model = config.get("Model").value
    system_message = config.get("System Message").value
    openai_key = get_environment(config, "API Key", "OPENAI_API_KEY")
    openai_url = get_environment(config, "URL", "OPENAI_BASE_URL")
    
    # Prepare messages
    messages = self.prepare_messages(
        query, context, conversation, system_message
    )
    
    # Setup request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_key}"
    }
    data = {
        "messages": messages,
        "model": model,
        "stream": True  # Enable streaming
    }
    
    # Stream response
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{openai_url}/chat/completions",
            json=data,
            headers=headers,
            timeout=None
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    if line.strip() == "data: [DONE]":
                        break
                    json_line = json.loads(line[6:])
                    choice = json_line["choices"][0]
                    
                    # Yield each token
                    if "delta" in choice and "content" in choice["delta"]:
                        yield {
                            "message": choice["delta"]["content"],
                            "finish_reason": choice.get("finish_reason")
                        }
```

#### Message Preparation

```python
def prepare_messages(
    self, query, context, conversation, system_message
):
    messages = [
        {
            "role": "system",
            "content": system_message
        }
    ]
    
    # Add conversation history
    for message in conversation:
        messages.append({
            "role": message.type,  # "user" or "assistant"
            "content": message.content
        })
    
    # Add current query with context
    messages.append({
        "role": "user",
        "content": f"Answer this query: '{query}' with this provided context: {context}"
    })
    
    return messages
```

**Example Message Array:**
```python
[
    {
        "role": "system",
        "content": "You are Verba, a chatbot for RAG..."
    },
    {
        "role": "user",
        "content": "What is machine learning?"
    },
    {
        "role": "assistant",
        "content": "Machine learning is..."
    },
    {
        "role": "user",
        "content": "Answer this query: 'Explain neural networks' with this provided context: [Retrieved chunks...]"
    }
]
```

### Anthropic Generator Implementation

**File:** `goldenverba/components/generation/AnthrophicGenerator.py`

#### Key Differences from OpenAI

**1. API Structure:**
```python
# Anthropic uses different headers
headers = {
    "Content-Type": "application/json",
    "x-api-key": antr_key,  # Different auth header
    "anthropic-version": "2023-06-01"
}

# System message is separate parameter
data = {
    "messages": messages,  # No system message here
    "model": model,
    "stream": True,
    "system": system_message,  # Separate field
    "max_tokens": 4096
}
```

**2. Message Roles:**
```python
# Anthropic uses "assistant" instead of "system" for AI responses
for message in conversation:
    messages.append({
        "role": "assistant" if message.type == "system" else message.type,
        "content": message.content
    })
```

**3. Streaming Format:**
```python
# Different JSON structure
async for line in response.content:
    line = line.decode("utf-8").strip()
    if line.startswith("data: "):
        json_line = json.loads(line[6:])
        
        # Check event type
        if json_line["type"] == "content_block_delta":
            delta = json_line.get("delta", {})
            if delta.get("type") == "text_delta":
                text = delta.get("text", "")
                yield {
                    "message": text,
                    "finish_reason": None
                }
        elif json_line.get("type") == "message_stop":
            yield {
                "message": "",
                "finish_reason": json_line.get("stop_reason", "stop")
            }
```

### Other Generator Implementations

**Available Generators:**
- `OllamaGenerator.py` - Local models (Llama3, Mistral)
- `CohereGenerator.py` - Cohere Command models
- `GroqGenerator.py` - Groq LPU inference
- `GeminiGenerator.py` - Google Gemini models
- `NovitaGenerator.py` - Novita AI models
- `UpstageGenerator.py` - Upstage Solar models

**Common Pattern:**
All generators follow the same interface:
1. Configure model and API settings
2. Implement `generate_stream()` for token streaming
3. Implement `prepare_messages()` for API-specific formatting
4. Handle errors and connection issues
5. Yield tokens in standard format: `{"message": str, "finish_reason": str|None}`

---

## Data Flow: Complete RAG Pipeline

### User Query → Response

```
1. User types query in textarea
   ↓
2. Frontend: sendUserMessage()
   - Adds user message to conversation
   - Sets status to "CHUNKS"
   ↓
3. API Call: POST /api/query
   - Sends: query, RAGConfig, filters, credentials
   ↓
4. Backend: VerbaManager.retrieve_chunks()
   - Embedder vectorizes query
   - Retriever searches Weaviate
   - WindowRetriever applies window technique
   - Returns: documents array + context string
   ↓
5. Frontend: Receives documents
   - Displays retrieval message with document cards
   - Updates right panel with first document
   - Sets status to "RESPONSE"
   ↓
6. WebSocket: /ws/generate_stream
   - Sends: query, context, conversation, RAGConfig
   ↓
7. Backend: Generator.generate_stream()
   - Prepares messages with context
   - Streams to LLM API
   - Yields tokens back through WebSocket
   ↓
8. Frontend: Receives tokens
   - Appends to previewText
   - Displays streaming response
   ↓
9. Completion: finish_reason = "stop"
   - Adds complete message to conversation
   - Sets status to "DONE"
   - Clears previewText
```

---

## Key UI Interactions

### Filtering Documents

**By Label:**
1. Click "Label" dropdown
2. Select label from list
3. Label appears as chip above chat
4. Query only searches documents with that label
5. Click X on chip to remove filter

**By Document:**
1. View retrieved documents in right panel
2. Click "Filter" button on document card
3. Document appears as chip above chat
4. Future queries only search that document
5. Click X on chip to remove filter

### Viewing Document Details

**From Chat:**
1. Query returns documents
2. Click document card in retrieval message
3. Right panel shows document details
4. Highlighted chunks show relevance scores

**Chunk Navigation:**
1. Use pagination controls
2. Click chunk to expand
3. See surrounding context
4. View chunk metadata

### Configuration Changes

**Switching Models:**
1. Click "Config" button
2. Select component (Embedder/Generator/Retriever)
3. Choose different model from dropdown
4. Click "Save Config"
5. Changes persist in Weaviate

**Adjusting Retrieval:**
1. Open Retriever config
2. Modify window size (0-10)
3. Adjust threshold (0-100)
4. Change limit mode (Autocut/Fixed)
5. Save to apply changes

---

## WebSocket Communication

### Connection Management

```typescript
// Establish connection
const socket = new WebSocket(socketHost);

socket.onopen = () => {
    setSocketOnline(true);
};

socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // Handle streaming tokens
    setPreviewText(prev => prev + data.message);
    
    if (data.finish_reason === "stop") {
        // Complete message
        setMessages(prev => [...prev, {
            type: "system",
            content: data.full_text
        }]);
    }
};

socket.onerror = () => {
    setSocketOnline(false);
    setReconnect(prev => !prev);  // Trigger reconnection
};
```

### Sending Generation Request

```typescript
const data = JSON.stringify({
    query: "User's question",
    context: "Retrieved context from documents",
    conversation: [
        {type: "user", content: "Previous question"},
        {type: "system", content: "Previous answer"}
    ],
    rag_config: RAGConfig
});
socket.send(data);
```

---

## Summary

**UI Components:**
- Two-panel responsive layout
- Real-time streaming responses
- Interactive document exploration
- Comprehensive filtering system
- Live configuration management

**Retriever:**
- Hybrid search (semantic + keyword)
- Intelligent window expansion
- Score-based context inclusion
- Document grouping and ranking

**Generator:**
- Pluggable LLM providers
- Streaming token generation
- Conversation history management
- Customizable system prompts
- Error handling and reconnection

The system provides a complete RAG experience with fine-grained control over every aspect of the pipeline, from document retrieval to response generation.
