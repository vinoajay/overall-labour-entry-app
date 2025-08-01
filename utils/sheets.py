import datetime
import gspread
from rapidfuzz import process
import streamlit as st
from google.oauth2.service_account import Credentials
import json
import logging

# ✅ Setup logger
logger = logging.getLogger(__name__)

# ✅ Auth using Streamlit secrets
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    raw_secret = st.secrets["GOOGLE_SERVICE_ACCOUNT"]

    if isinstance(raw_secret, str):
        service_account_info = json.loads(raw_secret)
    else:
        service_account_info = dict(raw_secret)

    creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    return gspread.authorize(creds)

def load_sheet():
    logger.info("🔄 Loading sheet from Streamlit Cloud secrets...")
    gc = get_gspread_client()
    sheet_id = st.secrets["GOOGLE_SHEET_ID"]
    sheet = gc.open_by_key(sheet_id)
    logger.info("✅ Sheet loaded successfully.")
    return sheet

@st.cache_data(ttl=3600)
def load_meta_info():
    logger.info("🔄 Loading Meta tab info...")
    sheet = load_sheet()
    try:
        meta = sheet.worksheet("Meta")
        data = meta.get_all_records()
        logger.info(f"📋 Meta rows found: {len(data)}")

        tabs = sorted(set(d["Team Name"] for d in data if d.get("Team Name")))
        sites = sorted(set(d["Site Name"] for d in data if d.get("Site Name")))
        logger.info(f"📌 Loaded {len(tabs)} team tabs and {len(sites)} site names.")
        return tabs, sites
    except Exception as e:
        logger.error(f"❌ Error loading Meta tab: {e}")
        return [], []

@st.cache_data(ttl=3600)
def load_sheet_dates():
    logger.info("🔄 Scanning worksheets for date columns...")
    sheet = load_sheet()
    all_dates = {}

    for worksheet in sheet.worksheets():
        logger.info(f"🧾 Checking tab: {worksheet.title}")
        values = worksheet.row_values(1)
        for col_idx, val in enumerate(values[3:], start=4):
            if val:
                try:
                    date_obj = datetime.datetime.strptime(val.strip(), "%d-%b-%Y")
                    all_dates[val.strip()] = col_idx
                except Exception:
                    continue

    logger.info(f"📅 Found {len(all_dates)} unique dates.")
    return list(all_dates.keys())

def find_site_row(worksheet, site_name):
    logger.info(f"🔍 Searching for site: {site_name}")
    site_col = worksheet.col_values(2)[2:]
    match, score, idx = process.extractOne(site_name.lower(), [s.lower() for s in site_col])
    logger.info(f"🧭 Matched '{site_name}' to '{match}' with score {score}")
    if score > 80:
        return idx + 3
    return None

def find_date_columns(worksheet, target_date_str):
    logger.info(f"🔍 Looking for date: {target_date_str}")
    row = worksheet.row_values(1)
    for col in range(3, len(row)):
        val = row[col]
        if val.strip() == target_date_str.strip():
            logger.info(f"✅ Date '{target_date_str}' found at columns {col + 1} (M), {col + 2} (H)")
            return col + 1, col + 2
    logger.info(f"❌ Date '{target_date_str}' not found.")
    return None, None

def write_attendance(sheet, entries):
    success_messages = []

    for entry in entries:
        tab = entry["tab"]
        site = entry["site"]
        date = entry["date"]
        attendance = entry["attendance"]

        try:
            worksheet = sheet.worksheet(tab)
        except Exception as e:
            msg = f"❌ Tab '{tab}' not found: {e}"
            logger.error(msg)
            success_messages.append(msg)
            continue

        try:
            data = worksheet.get_all_values()
        except Exception as e:
            msg = f"❌ Failed to load data from tab '{tab}': {e}"
            logger.error(msg)
            success_messages.append(msg)
            continue

        headers = data[0]
        rows = data[1:]

        row = None
        for idx, row_data in enumerate(rows, start=2):
            if len(row_data) > 1 and row_data[1].strip().lower() == site.strip().lower():
                row = idx
                break

        if not row:
            msg = f"❌ Site '{site}' not found in tab '{tab}'"
            logger.warning(msg)
            success_messages.append(msg)
            continue

        try:
            m_col = headers.index(date) + 1
            h_col = m_col + 1
        except ValueError:
            msg = f"❌ Date '{date}' not found in headers for tab '{tab}'"
            logger.warning(msg)
            success_messages.append(msg)
            continue

        if "M" in attendance:
            try:
                worksheet.update_cell(row, m_col, attendance["M"])
                msg = f"✅ Updated M ({attendance['M']}) at row {row}, col {m_col} in '{tab}'"
                logger.info(msg)
                success_messages.append(msg)
            except Exception as e:
                msg = f"❌ Failed to update M at row {row}, col {m_col}: {e}"
                logger.error(msg)
                success_messages.append(msg)

        if "H" in attendance:
            try:
                worksheet.update_cell(row, h_col, attendance["H"])
                msg = f"✅ Updated H ({attendance['H']}) at row {row}, col {h_col} in '{tab}'"
                logger.info(msg)
                success_messages.append(msg)
            except Exception as e:
                msg = f"❌ Failed to update H at row {row}, col {h_col}: {e}"
                logger.error(msg)
                success_messages.append(msg)

    return "\n".join(success_messages)
