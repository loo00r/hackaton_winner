from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)
MODEL = "gpt-4.1-mini"

llm_client = OpenAI()
