import os
import gspread
from dotenv import load_dotenv

load_dotenv()

def load_meta():
    SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
    gc = gspread.service_account(filename="credentials.json")
    sh = gc.open_by_key(SHEET_ID)
    meta_ws = sh.worksheet("Meta")

    data = meta_ws.get_all_records()

    tab_names = sorted(set(row["Tab Name"].strip() for row in data if row.get("Tab Name")))
    site_names = sorted(set(row["Site Name"].strip() for row in data if row.get("Site Name")))

    return {
        "tab_names": tab_names,
        "site_names": site_names
    }
