# TownSquare RAG System

A Retrieval-Augmented Generation (RAG) system built for strata management, using AWS Bedrock and Claude models.

## Overview

This system provides an AI-powered strata management assistant that can:

- Intelligently determine when to use RAG for answering queries
- Retrieve relevant information from building-specific and global knowledge bases
- Generate professional and accurate responses to client queries
- Maintain conversation context for natural interactions

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

## Configuration

Key configuration parameters in `rag.py`:

- `AWS_REGION`: Your AWS Bedrock region
- `KB_ID_GLOBAL`: Global knowledge base ID
- `KB_ID_BUILDING_A`: Building-specific knowledge base ID
- `GENERATION_MODEL_ID`: Main response generation model
- `JUDGE_MODEL_ID`: RAG necessity decision model

## Project Structure

- `rag.py`: Main implementation file
- `requirements.txt`: Project dependencies
- `.gitignore`: Git ignore rules
- `README.md`: Project documentation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Add your license here]

## Contact

[Add your contact information here]
