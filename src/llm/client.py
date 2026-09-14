from openai import OpenAI

MODEL = "gemma4:12b"

llm_client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)
