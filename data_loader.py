import requests
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict

KOLKATA = ZoneInfo("Asia/Kolkata")

# ========== PASTE YOUR REAL URLs HERE ==========
BASE = "https://exam.sanand.workers.dev/questionData?email=24f3004884%40ds.study.iitm.ac.in&quizSign=RqESB7XXeEqqvpm0KBEnuF8oMrzF%2FAm8DolehEKNjyW12DOGoQi%2B%2Fd5Y%2FpHFFnVP5B5v0uUAT7szcpEVqc6%2BdQIN40R8FfHEtWcLRBkZ0Rou3GwfiuLkLcCWfp8Pk%2BYXsFJxZXqPrlqbHM7mTj8DPrZyj%2F2MiwxhDWkYNXpdSD1DEThT3ykEDLWZvVBz3l4qoLTynDL24bhMGsJUrlhQ%2BxkTOVuwSVqBW7Ku2GNtLsM4UY860qs1iVz9E6vK6t3IZWTTSm5wfBBaCNTi9mgrt3ITNdMzeZmZJ1xjRLS%2BTOFtFdosuOX6xHwsWOrYnVGFhIBswzhurTjPZDfBkhJX4w%3D%3D&questionId=q-ledger-agent-server"

EXPORT_URL = BASE + "&path=%2Fexport"
RATES_URL  = BASE + "&path=%2Frates"
# ==============================================

def load_and_clean_orders() -> List[Dict]:
    print("Downloading rates...")
    rates = requests.get(RATES_URL, timeout=30).json()["usd_per_unit"]
    print("Rates:", rates)

    print("Downloading all orders from /export ...")
    resp = requests.get(EXPORT_URL, timeout=60)
    resp.raise_for_status()
    lines = resp.text.strip().splitlines()
    raw_orders = [json.loads(line) for line in lines]
    print(f"Raw rows downloaded: {len(raw_orders)}")

    # Keep only the latest version of each order id
    latest = {}
    for o in raw_orders:
        oid = o["id"]
        if oid not in latest or o["updated_at"] > latest[oid]["updated_at"]:
            latest[oid] = o

    clean = list(latest.values())
    print(f"Unique orders after deduplication: {len(clean)}")

    # Convert to USD + parse date in Asia/Kolkata
    for o in clean:
        rate = rates.get(o["currency"], 1.0)
        o["amount_usd"] = round(float(o["amount"]) * rate, 2)

        # Parse created_at → Asia/Kolkata
        dt_str = o["created_at"].replace("Z", "+00:00")
        dt = datetime.fromisoformat(dt_str)
        o["created_kolkata"] = dt.astimezone(KOLKATA)

    return clean