# TownSquare RAG System

A Retrieval-Augmented Generation (RAG) system built for strata management, using AWS Bedrock and Claude models.

## Overview

The Strata Management AI Assistant helps strata managers communicate more effectively with clients by generating professional, accurate draft responses based on specific bylaws, rules, and communication guidelines.

This system provides an AI-powered strata management assistant that can:

- Intelligently determine when to use RAG for answering queries
- Retrieve relevant information from building-specific and global knowledge bases
- Generate professional and accurate responses to client queries
- Maintain conversation context for natural interactions

## Key Benefits

- Ensures consistent, polite tone in all client communications
- Reduces response time by 40-60% for common queries
- Grounds all responses in factual building-specific information
- Scales easily across multiple buildings with different rules

## Features

- Conditional RAG implementation using a judge LLM
- Dual knowledge base retrieval (building-specific and global)
- Context-aware response generation
- Professional strata management communication
- AWS Bedrock integration with Claude models

## Prerequisites

- Python 3.8+
- AWS Account with Bedrock access
- AWS CLI configured
- Required Python packages (see requirements.txt)

## Setup

1. Clone the repository:

```bash
git clone [repository-url]
cd townsquare-poc
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Configure AWS credentials:

```bash
aws configure
```

5. Update the configuration in `rag.py`:

- Set your AWS region
- Add your Knowledge Base IDs
- Configure model parameters as needed

## Usage

Run the main script:

```bash
python rag.py
```

The system will prompt you to input messages as a client would. Type your queries and the system will generate professional responses. Type 'quit' or 'exit' to end the conversation.

## Configuration

Key configuration parameters in `rag.py`:

- `AWS_REGION`: Your AWS Bedrock region
- `KB_ID_GLOBAL`: Global knowledge base ID
- `KB_ID_BUILDING_A`: Building-specific knowledge base ID
- `GENERATION_MODEL_ID`: Main response generation model
- `JUDGE_MODEL_ID`: RAG necessity decision model
- `K_SPECIFIC`: Number of chunks from building-specific KB
- `K_GLOBAL`: Number of chunks from global KB
- `RAG_CONTEXT_TOKEN_LIMIT`: Max tokens for combined RAG context
- `MAX_TOKENS_TO_SAMPLE`: Maximum tokens for LLM response
- `TEMPERATURE`: Controls response randomness
- `TOP_P`: Controls diversity of responses

## Project Structure

- `rag.py`: Main implementation file
- `requirements.txt`: Project dependencies
- `.gitignore`: Git ignore rules
- `README.md`: Project documentation
- `docs/technical_design.md`: Technical design document
- `docs/product_features.md`: Product feature document

## Documentation

Find detailed documentation in the `docs/` directory:

- [Technical Design Document](docs/technical_design.md)
- [Product Features Document](docs/product_features.md)
