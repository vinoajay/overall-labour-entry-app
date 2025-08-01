import streamlit as st
from utils.sheets import load_meta_info, load_sheet_dates, write_attendance, load_sheet  # ✅ added load_sheet import

st.set_page_config(page_title="Labour Entry Bot", layout="wide")

st.title("👷 Labour Attendance Entry")
# ✅ Confirm secrets load (for first-time cloud deploy debug)


# ✅ Load dropdown options (cached)
meta_tabs, meta_sites = load_meta_info()
all_dates = load_sheet_dates()

selected_date = st.selectbox("Select Date", all_dates)

all_entries = []

st.markdown("### 👤 Enter Labour-wise Attendance")

for labor_index in range(10):
    with st.expander(f"Labour Entry {labor_index + 1}", expanded=False):
        selected_tab = st.selectbox(
            f"Select Team Tab (Labour {labor_index + 1})",
            meta_tabs,
            key=f"tab_{labor_index}"
        )

        for site_index in range(10):
            site_col = st.columns([3, 1, 1])

            selected_site = site_col[0].selectbox(
                f"Site {site_index + 1}",
                meta_sites,
                key=f"site_{labor_index}_{site_index}"
            )
            mason_count = site_col[1].number_input(
                "M", min_value=0, step=1, key=f"m_{labor_index}_{site_index}"
            )
            helper_count = site_col[2].number_input(
                "H", min_value=0, step=1, key=f"h_{labor_index}_{site_index}"
            )

            if mason_count > 0 or helper_count > 0:
                entry = {
                    "tab": selected_tab,
                    "site": selected_site,
                    "date": selected_date,
                    "attendance": {}
                }
                if mason_count > 0:
                    entry["attendance"]["M"] = mason_count
                if helper_count > 0:
                    entry["attendance"]["H"] = helper_count

                all_entries.append(entry)

# ✅ Preview the summary
st.markdown("### ✅ Summary of Entries")
if all_entries:
    st.json(all_entries)

# ✅ Final message + submit
if all_entries:
    st.markdown("### ✉️ Final Message to Write")
    final_message = ""
    for entry in all_entries:
        line = f"{entry['tab']} - {entry['site']} - {entry['date']}: "
        line += " ".join([f"{k}:{v}" for k, v in entry['attendance'].items()])
        final_message += line + "\n"

    st.text_area("Message Preview", final_message.strip(), height=200)

    # ✅ Load sheet only once here
    sheet = load_sheet()

    if st.button("✅ Send to Google Sheet"):
        log = write_attendance(sheet, all_entries)

        st.text_area("📝 Update Log", log, height=300)

        if "✅" in log:
            st.success("✅ Entries processed. Check log below for details.")
        else:
            st.error("❌ Some entries failed. Check log below.")
