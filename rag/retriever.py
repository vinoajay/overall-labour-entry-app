import json
import os
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from .embedder import get_embedding

# Load environment variables (if needed)
load_dotenv()

def load_site_data(meta_path="data/meta.json"):
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)

def retrieve_best_match(query, choices, threshold=0.7):
    query_embedding = np.array(get_embedding(query)).reshape(1, -1)

    best_match = None
    best_score = 0

    for choice in choices:
        choice_embedding = np.array(get_embedding(choice)).reshape(1, -1)
        score = cosine_similarity(query_embedding, choice_embedding)[0][0]

        if score > best_score and score >= threshold:
            best_score = score
            best_match = choice

    return best_match

def match_tab_name(input_text, tab_names):
    return retrieve_best_match(input_text, tab_names, threshold=0.65)

def match_site_name(input_text, site_names):
    return retrieve_best_match(input_text, site_names, threshold=0.65)
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

def get_parser_chain():
    prompt_template = PromptTemplate(
        input_variables=["message"],
        template="""
You are an expert assistant helping parse site labour messages. Given a message like:
"{message}"

Extract structured data as a JSON list. Each item should contain:
- "tab": team name
- "site": site name
- "date": actual date (interpret "today", "yesterday", etc.)
- "attendance": like "2M 1H"

Example Output:
[
    {{
        "tab": "SANKAR ENTRY",
        "site": "veeraganur",
        "date": "2025-07-25",
        "attendance": "2M 1H"
    }}
]
Only return the JSON.
""",
    )

    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    return LLMChain(llm=llm, prompt=prompt_template)
