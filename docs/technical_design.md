# Technical Design Document: Strata Management AI Assistant

## 1. Introduction

### Problem Statement

Strata managers often spend significant time crafting responses to client inquiries, especially when referencing specific bylaws or building information. Responses can sometimes be perceived as rude or overly blunt, affecting client relations.

### Solution Overview

The Strata Management AI Assistant leverages AWS Bedrock's capabilities and Retrieval-Augmented Generation (RAG) to generate polite, professional, and accurate draft responses grounded in relevant documents and contextual conversation history.

## 2. System Architecture

The system follows a modular architecture with these key components:

### 2.1 Knowledge Base Layer

- **Global Knowledge Base**: Contains documents applicable to all buildings/schemas (legislation, company-wide guidelines)
- **Building-Specific Knowledge Bases**: Separate KBs for each building containing unique bylaws, rules, and documentation

### 2.2 Document Management Layer

- **S3 Storage**: Organizes documents in prefixes (`global/`, `building_A/`, etc.)
- **KB Synchronization**: Lambda function that triggers Bedrock ingestion jobs when documents are updated

### 2.3 RAG Processing Layer

- **RAG Necessity Judge**: Uses a smaller, faster LLM to determine if retrieval is necessary
- **Multi-KB Retriever**: Queries both building-specific and global KBs
- **Context Manager**: Combines and limits retrieved chunks based on relevance and token limits

### 2.4 Response Generation Layer

- **Prompt Assembly**: Combines system instructions, conversation history, RAG context, and query
- **LLM Integration**: Uses Bedrock's high-quality generation models (Claude 3)

### 2.5 API & Integration Layer

- **Conversation Management**: Maintains chat history and building context
- **API Endpoints**: Handles client-side requests and returns generated drafts

## 3. Data Flow Diagrams

### 3.1 Document Ingestion Flow

1. Strata manager uploads document to frontend
2. Frontend uploads to corresponding S3 prefix based on document type (global/building-specific)
3. S3 triggers Lambda via ObjectCreated event
4. Lambda identifies target KB based on S3 path
5. Lambda calls Bedrock StartIngestionJob to update KB

### 3.2 AI Response Generation Flow

1. Client message received, linked to specific building context
2. System formats recent conversation history
3. Judge LLM evaluates if RAG is necessary based on query and history
4. If RAG needed:
   - Retrieve from building-specific KB (k=2)
   - Retrieve from global KB (k=1)
   - Combine chunks and limit to token budget
5. Generate prompt with:
   - System instructions
   - Conversation history
   - RAG context (if available)
   - Client query
6. Call Bedrock with generation LLM (Claude 3)
7. Return draft to strata manager for review
8. Manager edits and sends, updating conversation history

## 4. RAG Implementation Details

### 4.1 RAG Necessity Check

```python
def needs_rag_check(history_str, latest_query, judge_llm_id):
    prompt = f"""Analyze the following user message in the context of an ongoing conversation between a client and a strata manager.
Determine if answering this message likely requires retrieving specific information from the building's bylaws, rules, FAQs, or other knowledge base documents.
Respond with only 'YES' or 'NO'.

Conversation History (Last few turns):
{history_str}

Latest User Message:
{latest_query}

Requires Knowledge Base Retrieval (YES/NO):
"""
    decision = invoke_llm(judge_llm_id, prompt, max_tokens=10, temp=0.0).strip().upper()
    return decision == "YES"
```

### 4.2 Multi-KB Retrieval

```python
# Retrieve from building-specific KB
specific_chunks_raw = retrieve_from_kb(KB_ID_BUILDING_A, query, K_SPECIFIC)

# Retrieve from global KB
global_chunks_raw = retrieve_from_kb(KB_ID_GLOBAL, query, K_GLOBAL)
```

### 4.3 Context Combination & Limitation

```python
# Sort by relevance score
retrieved_chunks_info.sort(key=lambda x: x['score'], reverse=True)

# Add chunks until token limit is reached
current_rag_tokens = 0
final_chunks_for_context = []
for chunk_info in retrieved_chunks_info:
    chunk_token_count = get_token_count(chunk_info['text'])

    if current_rag_tokens + chunk_token_count <= RAG_CONTEXT_TOKEN_LIMIT:
        final_chunks_for_context.append(chunk_info['text'])
        current_rag_tokens += chunk_token_count
    else:
        break
```

## 5. API Structure

### 5.1 Key Endpoints

- `/documents/upload`: Upload and categorize documents
- `/knowledge-bases/sync`: Trigger KB synchronization
- `/chat/history/{building_id}`: Retrieve conversation history
- `/chat/generate`: Generate draft response

### 5.2 Request/Response Examples

**Response Generation Request:**

```json
{
  "building_id": "building_A",
  "client_message": "What are the rules about parking in visitor spots?",
  "conversation_history": [
    { "role": "client", "message": "Hello, I have a question about parking." },
    {
      "role": "manager",
      "message": "Hi there! I'd be happy to help with your parking question."
    }
  ]
}
```

**Response Generation Response:**

```json
{
  "draft_response": "According to Building A's bylaws (Section 12.3), visitor parking spots are limited to a maximum stay of 24 hours per visit, with no more than 3 visits per week for the same vehicle. Residents are not permitted to use visitor spots at any time. If you have guests staying longer, please contact the management office to arrange for extended parking permissions.",
  "sources": [
    { "source": "Building_A_Bylaws.pdf", "section": "Section 12.3" },
    { "source": "Global_Parking_Guidelines.pdf", "section": "General Rules" }
  ],
  "rag_used": true
}
```

## 6. Configuration Parameters

| Parameter                 | Default                                   | Description                                |
| ------------------------- | ----------------------------------------- | ------------------------------------------ |
| `AWS_REGION`              | "ap-southeast-2"                          | AWS Bedrock region                         |
| `KB_ID_GLOBAL`            | ""                                        | Global knowledge base ID                   |
| `KB_ID_BUILDING_A`        | ""                                        | Building A knowledge base ID               |
| `GENERATION_MODEL_ID`     | "anthropic.claude-3-sonnet-20240229-v1:0" | Model for response generation              |
| `JUDGE_MODEL_ID`          | "anthropic.claude-3-haiku-20240307-v1:0"  | Model for RAG necessity check              |
| `K_SPECIFIC`              | 2                                         | Number of chunks from building-specific KB |
| `K_GLOBAL`                | 1                                         | Number of chunks from global KB            |
| `RAG_CONTEXT_TOKEN_LIMIT` | 4000                                      | Max tokens for combined RAG context        |
| `MAX_TOKENS_TO_SAMPLE`    | 1000                                      | Maximum tokens in generated response       |
| `TEMPERATURE`             | 0.2                                       | Controls response randomness               |
| `TOP_P`                   | 0.9                                       | Controls diversity of responses            |

## 7. Error Handling

### 7.1 Common Error Scenarios

- KB retrieval failures
- LLM service disruptions
- Token limit exceeded
- Insufficient information in KBs

### 7.2 Fallback Mechanisms

- Use history-only generation if RAG fails
- Clearly indicate to managers when responses are not KB-grounded
- Default to lower-latency models in high traffic

## 8. Deployment Considerations

### 8.1 Infrastructure Requirements

- AWS Bedrock with appropriate model access
- S3 bucket for document storage
- Lambda functions for document processing
- API Gateway for frontend integration

### 8.2 Scaling Considerations

- Monitor Bedrock API limits
- Consider batched KB updates for large document sets
- Implement caching for frequently accessed KB chunks

## 9. Future Enhancements

### 9.1 Technical Improvements

- Implement document preprocessing for better chunking
- Add conversation summarization for longer exchanges
- Explore hybrid retrieval methods
- Add KB analytics for content optimization

### 9.2 Feature Enhancements

- Cross-building knowledge sharing
- Response template integration
- Multi-language support
- Automated follow-up suggestions
