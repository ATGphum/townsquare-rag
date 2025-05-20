import boto3
import json
import time # For potential delays or just to see execution time

# --- Configuration ---
AWS_REGION = "ap-southeast-2" # Or your Bedrock region
KB_ID_GLOBAL = ""  # Replace with your actual Global KB ID
KB_ID_BUILDING_A = "YOUR_BUILDING_A_KB_ID" # Replace with your Building A KB ID
GENERATION_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0" # Or your preferred model
# GENERATION_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0" # For cost/speed testing
JUDGE_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0" # For the RAG necessity check

# RAG Parameters
K_SPECIFIC = 2  # Number of chunks from building-specific KB
K_GLOBAL = 1    # Number of chunks from global KB
RAG_CONTEXT_TOKEN_LIMIT = 2000 # Max tokens for combined RAG context

# LLM Generation Parameters
MAX_TOKENS_TO_SAMPLE = 1000
TEMPERATURE = 0.2
TOP_P = 0.9 # Can use top_p or top_k, often not both with temperature

# Initialize Boto3 clients
bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime', region_name=AWS_REGION)
bedrock_runtime_client = boto3.client('bedrock-runtime', region_name=AWS_REGION)

# --- Helper Functions ---

def invoke_llm(model_id, prompt, max_tokens=MAX_TOKENS_TO_SAMPLE, temp=TEMPERATURE, top_p_val=TOP_P):
    """Invokes a Bedrock LLM for text generation."""
    body = {
        "anthropic_version": "bedrock-2023-05-31", # Required for Claude 3
        "max_tokens": max_tokens,
        "temperature": temp,
        "top_p": top_p_val,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}]
            }
        ]
    }
    try:
        response = bedrock_runtime_client.invoke_model(
            body=json.dumps(body),
            modelId=model_id,
            contentType='application/json',
            accept='application/json'
        )
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']
    except Exception as e:
        print(f"Error invoking LLM {model_id}: {e}")
        return f"Error: Could not get response from LLM. {e}"

def retrieve_from_kb(kb_id, query_text, num_results):
    """Retrieves chunks from a specified Bedrock Knowledge Base."""
    try:
        response = bedrock_agent_runtime_client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={
                'text': query_text
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': num_results
                }
            }
        )
        return response.get('retrievalResults', [])
    except Exception as e:
        print(f"Error retrieving from KB {kb_id}: {e}")
        return []

def get_token_count(text_content):
    """
    Placeholder for token counting.
    For accurate counting, use a library like tiktoken for Anthropic/OpenAI models.
    This is a VERY rough approximation.
    """
    return len(text_content.split()) # Highly inaccurate, use tiktoken for real apps!

def needs_rag_check(history_str, latest_query, judge_llm_id):
    """Uses a 'Judge' LLM to determine if RAG is needed."""
    print("\n--- RAG Necessity Check ---")
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
    print(f"Judge LLM decision: {decision}")
    return decision == "YES"

# --- Main Test Logic ---

# Simulate a conversation
conversation_history = [
    {"role": "client", "message": "Hi, I have a question about the upcoming AGM for Building A."},
    {"role": "manager_ai_draft", "message": "Hello! I can help with that. The AGM for Building A is scheduled. What specific information are you looking for?"},
    {"role": "client", "message": "When is it and what's the deadline for submitting agenda items?"} # This is our current query
]

def format_history_for_prompt(history_list, num_turns=6):
    """Formats the last N turns of history for the prompt."""
    formatted_history = []
    for turn in history_list[-num_turns:]: # Get last N turns
        role_label = "Client" if turn["role"] == "client" else "Manager (AI)"
        formatted_history.append(f"{role_label}: {turn['message']}")
    return "\n".join(formatted_history)

# Get the latest query and formatted history
latest_client_query = conversation_history[-1]["message"]
managed_history_for_prompt = format_history_for_prompt(conversation_history[:-1]) # History before the latest query

print(f"Latest Client Query: {latest_client_query}")
print(f"Managed History for Prompt:\n{managed_history_for_prompt}")

# 1. Conditional RAG Check
rag_needed = needs_rag_check(managed_history_for_prompt, latest_client_query, JUDGE_MODEL_ID)

combined_rag_context = ""
retrieved_chunks_info = []

if rag_needed:
    print("\n--- RAG Retrieval Initiated ---")
    # 2. Retrieve from Building-Specific KB
    print(f"Retrieving from Building KB: {KB_ID_BUILDING_A} ({K_SPECIFIC} results)")
    specific_chunks_raw = retrieve_from_kb(KB_ID_BUILDING_A, latest_client_query, K_SPECIFIC)
    for i, chunk_data in enumerate(specific_chunks_raw):
        retrieved_chunks_info.append({
            "text": chunk_data['content']['text'],
            "score": chunk_data.get('score', 0), # Score might not always be present or easily comparable across KBs
            "source": f"Building_A_Chunk_{i+1}"
        })
        print(f"  Retrieved Specific Chunk {i+1} (Score: {chunk_data.get('score', 'N/A')})")


    # 3. Retrieve from Global KB
    print(f"Retrieving from Global KB: {KB_ID_GLOBAL} ({K_GLOBAL} results)")
    global_chunks_raw = retrieve_from_kb(KB_ID_GLOBAL, latest_client_query, K_GLOBAL)
    for i, chunk_data in enumerate(global_chunks_raw):
        retrieved_chunks_info.append({
            "text": chunk_data['content']['text'],
            "score": chunk_data.get('score', 0),
            "source": f"Global_Chunk_{i+1}"
        })
        print(f"  Retrieved Global Chunk {i+1} (Score: {chunk_data.get('score', 'N/A')})")

    # 4. Combine and Limit RAG Context (Simplified for this example - using score as rough sort key)
    # A more robust solution would normalize scores or use a more sophisticated ranking if scores differ wildly.
    # For now, we'll just combine and then truncate based on token count.
    retrieved_chunks_info.sort(key=lambda x: x['score'], reverse=True) # Sort by score (descending)

    current_rag_tokens = 0
    final_chunks_for_context = []
    for chunk_info in retrieved_chunks_info:
        # IMPORTANT: Use a real tokenizer here for accurate token counting!
        # For Claude models, you can use the 'anthropic' library or tiktoken with appropriate model name.
        # For example, with tiktoken:
        # import tiktoken
        # cl100k_base = tiktoken.get_encoding("cl100k_base")
        # chunk_token_count = len(cl100k_base.encode(chunk_info['text']))

        chunk_token_count = get_token_count(chunk_info['text']) # Using placeholder

        if current_rag_tokens + chunk_token_count <= RAG_CONTEXT_TOKEN_LIMIT:
            final_chunks_for_context.append(chunk_info['text'])
            current_rag_tokens += chunk_token_count
        else:
            print(f"RAG context token limit ({RAG_CONTEXT_TOKEN_LIMIT}) reached. Skipping further chunks.")
            break

    combined_rag_context = "\n\n---\n\n".join(final_chunks_for_context)
    print(f"\nCombined RAG Context ({current_rag_tokens} approx. tokens):\n{combined_rag_context[:1000]}...") # Print first 1000 chars
else:
    print("\n--- RAG Skipped based on Judge LLM ---")


# 5. Prepare Final Prompt for Generation LLM
system_prompt = """You are an AI assistant helping a strata manager communicate professionally with clients.
Your task is to generate a polite, accurate, and helpful draft response.

**Instructions:**
- Base your response strictly on the information within the "CONTEXT DOCUMENTS" section if provided.
- Refer to the "CHAT HISTORY" for conversational flow and context.
- If context documents are provided and they don't contain the answer, clearly state that you cannot provide the information based on the documents available. Do not invent answers if context is meant to be used.
- If no context documents are provided (RAG was skipped), provide a helpful conversational response based on the chat history.
- Maintain a professional, polite, and empathetic tone. Avoid dismissive or rude language.
- Address the user's latest query directly.
- Do not provide legal advice.
"""

final_prompt_parts = [system_prompt]

if managed_history_for_prompt:
    final_prompt_parts.append(f"\n--- CHAT HISTORY (Recent Turns) ---\n{managed_history_for_prompt}")

if combined_rag_context: # Only add context if RAG was performed and yielded results
    final_prompt_parts.append(f"\n\n--- CONTEXT DOCUMENTS ---\n{combined_rag_context}")

final_prompt_parts.append(f"\n\n--- CURRENT QUERY ---\n{latest_client_query}")
final_prompt_parts.append("\n\nDraft Response:")

final_prompt_for_generation = "".join(final_prompt_parts)

print(f"\n--- Final Prompt for Generation LLM (first 500 chars) ---\n{final_prompt_for_generation[:500]}...")

# 6. Generate Response
print(f"\n--- Generating Draft Response using {GENERATION_MODEL_ID} ---")
start_time = time.time()
ai_draft_response = invoke_llm(GENERATION_MODEL_ID, final_prompt_for_generation)
end_time = time.time()

print(f"\n\n================ AI DRAFT RESPONSE (Generated in {end_time - start_time:.2f}s) ================")
print(ai_draft_response)
print("====================================================================")

# 7. (Simulate Manager Action) Add AI response to history if used
# conversation_history.append({"role": "manager_ai_draft", "message": ai_draft_response})