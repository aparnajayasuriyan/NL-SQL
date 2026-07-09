# DataBridge - Making data accessible to everyone

A Streamlit-based AI-powered SQL analytics assistant that uses Ollama to translate natural language questions into SQLite queries.

## Features

- Demo mode with an in-memory sample SQLite database
- Connect to an external SQLite database file
- Generate SQL from natural language using the Ollama Python client
- Display query results directly in the Streamlit UI
- Save Ollama configuration via session state

## Requirements

- Python 3.11+ (or compatible Python 3.x)
- `pandas`
- `streamlit`
- `ollama`

Install runtime dependencies with:

```bash
python -m pip install -r requirements.txt
```

## Setup

1. Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set Ollama environment variables or create a `secrets.env` file in the repository root with:

```env
OLLAMA_API_KEY=your_api_key_here
OLLAMA_ENDPOINT=https://ollama.com/
OLLAMA_MODEL=gemma3:27b
```

## Run

Start the Streamlit app from the repository root:

```bash
streamlit run sql_agent.py
```

Then open the displayed local URL in your browser.

## Usage

- Use the `Settings` tab to configure the Ollama API key, endpoint, and model.
- Use the `Database` tab to choose between demo mode or connect to a local SQLite database.
- Use the `Query` tab to enter natural language questions and generate SQL.

## Notes

- The app currently supports only SQLite databases.
- The Ollama client is used to generate SQL prompts and may require a local or cloud Ollama service.
