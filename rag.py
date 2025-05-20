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
RAG_CONTEXT_TOKEN_LIMIT = 4000 # Max tokens for combined RAG context

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

def format_history_for_prompt(history_list, num_turns=6):
    """Formats the last N turns of history for the prompt."""
    formatted_history = []
    for turn in history_list[-num_turns:]: # Get last N turns
        role_label = "Client" if turn["role"] == "client" else "Manager (AI)"
        formatted_history.append(f"{role_label}: {turn['message']}")
    return "\n".join(formatted_history)

def process_query(query, conversation_history):
    """Process a single query and return the AI response."""
    managed_history_for_prompt = format_history_for_prompt(conversation_history)
    
    # 1. Conditional RAG Check
    rag_needed = needs_rag_check(managed_history_for_prompt, query, JUDGE_MODEL_ID)
    
    combined_rag_context = ""
    retrieved_chunks_info = []
    
    if rag_needed:
        print("\n--- RAG Retrieval Initiated ---")
        # 2. Retrieve from Building-Specific KB
        print(f"Retrieving from Building KB: {KB_ID_BUILDING_A} ({K_SPECIFIC} results)")
        specific_chunks_raw = retrieve_from_kb(KB_ID_BUILDING_A, query, K_SPECIFIC)
        for i, chunk_data in enumerate(specific_chunks_raw):
            retrieved_chunks_info.append({
                "text": chunk_data['content']['text'],
                "score": chunk_data.get('score', 0),
                "source": f"Building_A_Chunk_{i+1}"
            })
            print(f"  Retrieved Specific Chunk {i+1} (Score: {chunk_data.get('score', 'N/A')})")

        # 3. Retrieve from Global KB
        print(f"Retrieving from Global KB: {KB_ID_GLOBAL} ({K_GLOBAL} results)")
        global_chunks_raw = retrieve_from_kb(KB_ID_GLOBAL, query, K_GLOBAL)
        for i, chunk_data in enumerate(global_chunks_raw):
            retrieved_chunks_info.append({
                "text": chunk_data['content']['text'],
                "score": chunk_data.get('score', 0),
                "source": f"Global_Chunk_{i+1}"
            })
            print(f"  Retrieved Global Chunk {i+1} (Score: {chunk_data.get('score', 'N/A')})")

        # 4. Combine and Limit RAG Context
        retrieved_chunks_info.sort(key=lambda x: x['score'], reverse=True)
        
        current_rag_tokens = 0
        final_chunks_for_context = []
        for chunk_info in retrieved_chunks_info:
            chunk_token_count = get_token_count(chunk_info['text'])
            
            if current_rag_tokens + chunk_token_count <= RAG_CONTEXT_TOKEN_LIMIT:
                final_chunks_for_context.append(chunk_info['text'])
                current_rag_tokens += chunk_token_count
            else:
                print(f"RAG context token limit ({RAG_CONTEXT_TOKEN_LIMIT}) reached. Skipping further chunks.")
                break

        combined_rag_context = "\n\n---\n\n".join(final_chunks_for_context)
        print(f"\nCombined RAG Context ({current_rag_tokens} approx. tokens):\n{combined_rag_context[:1000]}...")
    else:
        print("\n--- RAG Skipped based on Judge LLM ---")

    # 5. Prepare Final Prompt
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

    if combined_rag_context:
        final_prompt_parts.append(f"\n\n--- CONTEXT DOCUMENTS ---\n{combined_rag_context}")

    final_prompt_parts.append(f"\n\n--- CURRENT QUERY ---\n{query}")
    final_prompt_parts.append("\n\nDraft Response:")

    final_prompt_for_generation = "".join(final_prompt_parts)

    # 6. Generate Response
    print(f"\n--- Generating Draft Response using {GENERATION_MODEL_ID} ---")
    start_time = time.time()
    ai_draft_response = invoke_llm(GENERATION_MODEL_ID, final_prompt_for_generation)
    end_time = time.time()

    print(f"\n\n================ AI DRAFT RESPONSE (Generated in {end_time - start_time:.2f}s) ================")
    print(ai_draft_response)
    print("====================================================================")
    
    return ai_draft_response

def main():
    """Main interactive conversation loop."""
    print("Welcome to the Strata Manager AI Assistant!")
    print("Type 'quit' or 'exit' to end the conversation.")
    print("----------------------------------------")
    
    conversation_history = []
    
    while True:
        # Get user input
        user_input = input("\nYou: ").strip()
        
        # Check for exit command
        if user_input.lower() in ['quit', 'exit']:
            print("\nThank you for using the Strata Manager AI Assistant. Goodbye!")
            break
            
        # Add user message to history
        conversation_history.append({"role": "client", "message": user_input})
        
        # Process the query and get AI response
        ai_response = process_query(user_input, conversation_history)
        
        # Add AI response to history
        conversation_history.append({"role": "manager_ai_draft", "message": ai_response})

if __name__ == "__main__":
    main()