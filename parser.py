import datetime
import re
from rag.retriever import get_parser_chain
from utils.meta_loader import load_meta
from rapidfuzz import process

# Load team and site names from Meta tab for fuzzy matching
meta = load_meta()
ALL_SITE_NAMES = meta["site_names"]
ALL_TAB_NAMES = meta["tab_names"]

def resolve_date(raw_date: str):
    today = datetime.date.today()
    raw_date = raw_date.lower()
    if "today" in raw_date:
        return today.strftime("%d-%m-%Y")
    elif "yesterday" in raw_date:
        return (today - datetime.timedelta(days=1)).strftime("%d-%m-%Y")
    else:
        # Try to match dd-mm-yyyy format
        match = re.search(r"\d{1,2}-\d{1,2}-\d{4}", raw_date)
        if match:
            return match.group()
    return today.strftime("%d-%m-%Y")  # fallback

def fuzzy_match_site(raw_site: str):
    match, score, _ = process.extractOne(raw_site, ALL_SITE_NAMES, score_cutoff=50)
    return match if match else raw_site

def fuzzy_match_tab(raw_tab: str):
    match, score, _ = process.extractOne(raw_tab, ALL_TAB_NAMES, score_cutoff=50)
    return match if match else raw_tab

def safe_parse_int(value):
    try:
        return int(value)
    except:
        return 0

def parse_labour_message(text):

    chain = get_parser_chain()
    response = chain.run(text)
    
    try:
        parsed = eval(response.strip())
    except Exception as e:
        print("Error parsing LLM output:", e)
        return []

    final_entries = []
    for item in parsed:
        if not item.get("site") or not item.get("tab"):
            continue
        site = fuzzy_match_site(item["site"])
        tab = fuzzy_match_tab(item["tab"])
        date = resolve_date(item.get("date", "today"))

        final_entries.append({
            "tab": tab,
            "site": site,
            "date": date,
            "M": safe_parse_int(item.get("M", 0)),
            "P": safe_parse_int(item.get("P", 0)),
            "H": safe_parse_int(item.get("H", 0)),
            "attendance": item.get("attendance", "")
        })

    return final_entries
