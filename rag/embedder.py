import os
from dotenv import load_dotenv
import openai

# Load environment variables from .env
load_dotenv()

# Get OpenAI API key and embedding model
openai.api_key = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "text-embedding-3-small")

def get_embedding(text: str) -> list:
    response = openai.Embedding.create(
        input=text,
        model=MODEL_NAME
    )
    return response['data'][0]['embedding']
