import os
import datetime
import gspread
from dotenv import load_dotenv
from rapidfuzz import process
import streamlit as st  # Required for caching
from google.oauth2.service_account import Credentials

load_dotenv()
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

# ⚙️ Sheet loading - not cached (used once and passed around)
def load_sheet():
    print("🔄 Loading sheet...")
    creds_dict = st.secrets["firebase"]  # 👈 From secrets.toml
    creds = Credentials.from_service_account_info(dict(creds_dict))
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(SHEET_ID)
    print("✅ Sheet loaded successfully.")
    return sheet

# ✅ Cached for 1 hour to reduce quota usage
@st.cache_data(ttl=3600)
def load_meta_info():
    print("🔄 Loading Meta tab info...")
    sheet = load_sheet()
    try:
        meta = sheet.worksheet("Meta")
        data = meta.get_all_records()
        print(f"📋 Meta rows found: {len(data)}")

        tabs = sorted(set(d["Team Name"] for d in data if d.get("Team Name")))
        sites = sorted(set(d["Site Name"] for d in data if d.get("Site Name")))
        print(f"📌 Loaded {len(tabs)} team tabs and {len(sites)} site names.")
        return tabs, sites
    except Exception as e:
        print(f"❌ Error loading Meta tab: {e}")
        return [], []

@st.cache_data(ttl=3600)
def load_sheet_dates():
    print("🔄 Scanning worksheets for date columns...")
    sheet = load_sheet()
    all_dates = {}

    for worksheet in sheet.worksheets():
        print(f"🧾 Checking tab: {worksheet.title}")
        values = worksheet.row_values(1)
        for col_idx, val in enumerate(values[3:], start=4):  # Start from column D
            if val:
                try:
                    date_obj = datetime.datetime.strptime(val.strip(), "%d-%b-%Y")
                    all_dates[val.strip()] = col_idx
                except Exception:
                    continue

    print(f"📅 Found {len(all_dates)} unique dates.")
    return list(all_dates.keys())

def find_site_row(worksheet, site_name):
    print(f"🔍 Searching for site: {site_name}")
    site_col = worksheet.col_values(2)[2:]  # B3 onwards
    match, score, idx = process.extractOne(site_name.lower(), [s.lower() for s in site_col])
    print(f"🧭 Matched '{site_name}' to '{match}' with score {score}")
    if score > 80:
        return idx + 3  # Adjust for starting at row 3
    return None

def find_date_columns(worksheet, target_date_str):
    print(f"🔍 Looking for date: {target_date_str}")
    row = worksheet.row_values(1)
    for col in range(3, len(row)):  # Start from D (index 3)
        val = row[col]
        if val.strip() == target_date_str.strip():
            print(f"✅ Date '{target_date_str}' found at columns {col + 1} (M), {col + 2} (H)")
            return col + 1, col + 2
    print(f"❌ Date '{target_date_str}' not found.")
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
            print(msg)
            success_messages.append(msg)
            continue

        try:
            data = worksheet.get_all_values()
        except Exception as e:
            msg = f"❌ Failed to load data from tab '{tab}': {e}"
            print(msg)
            success_messages.append(msg)
            continue

        headers = data[0]
        rows = data[1:]

        # Find row for site (use fuzzy match if needed)
        row = None
        for idx, row_data in enumerate(rows, start=2):  # 1-based index + header
            if len(row_data) > 1 and row_data[1].strip().lower() == site.strip().lower():
                row = idx
                break

        if not row:
            msg = f"❌ Site '{site}' not found in tab '{tab}'"
            print(msg)
            success_messages.append(msg)
            continue

        # Find columns for M, H
        try:
            m_col = headers.index(date) + 1
            h_col = m_col + 1
        except ValueError:
            msg = f"❌ Date '{date}' not found in headers for tab '{tab}'"
            print(msg)
            success_messages.append(msg)
            continue

        # Update M if exists
        if "M" in attendance:
            try:
                worksheet.update_cell(row, m_col, attendance["M"])
                msg = f"✅ Updated M ({attendance['M']}) at row {row}, col {m_col} in '{tab}'"
                print(msg)
                success_messages.append(msg)
            except Exception as e:
                msg = f"❌ Failed to update M at row {row}, col {m_col}: {e}"
                print(msg)
                success_messages.append(msg)

        # Update H if exists
        if "H" in attendance:
            try:
                worksheet.update_cell(row, h_col, attendance["H"])
                msg = f"✅ Updated H ({attendance['H']}) at row {row}, col {h_col} in '{tab}'"
                print(msg)
                success_messages.append(msg)
            except Exception as e:
                msg = f"❌ Failed to update H at row {row}, col {h_col}: {e}"
                print(msg)
                success_messages.append(msg)

    return "\n".join(success_messages)
