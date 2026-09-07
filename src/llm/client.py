from openai import OpenAI
import os
from dotenv import load_dotenv

# my_oauth_provider має бути оголошений або імпортований тут
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")

llm_client = OpenAI(
    api_key=API_KEY  # required but ignored
)