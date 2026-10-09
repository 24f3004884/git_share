from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List, Dict
import re
from data_loader import load_and_clean_orders

app = FastAPI(title="Acme Ledger Agent")

# ---------- Load data once at startup ----------
print("Loading and cleaning orders...")
ORDERS: List[Dict] = load_and_clean_orders()
print("Ready to answer questions.")

class Question(BaseModel):
    question: str

# ---------- Helper functions ----------

# ... (keep your ORDERS loading and Question model)
from collections import defaultdict
from typing import Optional, List, Dict, Set
import re

# ============================================================
# Helper functions
# ============================================================
from collections import defaultdict
from typing import Optional, List, Dict, Set
import re

# ============================================================
# Core filter
# ============================================================

def filter_orders(
    region: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    product: Optional[str] = None,
    customer: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Dict]:
    result = []
    for o in ORDERS:
        if status is not None and o["status"] != status:
            continue
        if region is not None and o["region"].lower() != region.lower():
            continue
        if product is not None and o["product"].lower() != product.lower():
            continue
        if customer is not None and o["customer"].lower() != customer.lower():
            continue
        if year is not None and o["created_kolkata"].year != year:
            continue
        if month is not None and o["created_kolkata"].month != month:
            continue
        result.append(o)
    return result

# ============================================================
# Metrics
# ============================================================

def calculate_revenue(**kwargs) -> float:
    orders = filter_orders(**kwargs)
    return round(sum(o["amount_usd"] for o in orders), 2)

def count_orders(**kwargs) -> int:
    return len(filter_orders(**kwargs))

def count_unique_customers(**kwargs) -> int:
    return len({o["customer"] for o in filter_orders(**kwargs)})

def count_unique_products(**kwargs) -> int:
    return len({o["product"] for o in filter_orders(**kwargs)})

def average_order_value(**kwargs) -> float:
    orders = filter_orders(**kwargs)
    if not orders:
        return 0.0
    total = sum(o["amount_usd"] for o in orders)
    return round(total / len(orders), 2)

def total_quantity(**kwargs) -> int:
    return sum(o.get("qty", 1) for o in filter_orders(**kwargs))

def get_top_product(**kwargs) -> str:
    kwargs.pop("status", None)
    orders = filter_orders(status="paid", **kwargs)
    rev = defaultdict(float)
    for o in orders:
        rev[o["product"]] += o["amount_usd"]
    return max(rev.items(), key=lambda x: x[1])[0] if rev else "None"

def get_top_region(**kwargs) -> str:
    kwargs.pop("status", None)
    orders = filter_orders(status="paid", **kwargs)
    rev = defaultdict(float)
    for o in orders:
        rev[o["region"]] += o["amount_usd"]
    return max(rev.items(), key=lambda x: x[1])[0] if rev else "None"

def get_top_customer(**kwargs) -> str:
    kwargs.pop("status", None)
    orders = filter_orders(status="paid", **kwargs)
    rev = defaultdict(float)
    for o in orders:
        rev[o["customer"]] += o["amount_usd"]
    return max(rev.items(), key=lambda x: x[1])[0] if rev else "None"

def get_all_products() -> Set[str]:
    return {o["product"] for o in ORDERS}

# ============================================================
# Parser – more patterns
# ============================================================

def parse_question(q: str) -> dict:
    q_lower = q.lower().strip()
    result = {
        "type": "revenue",
        "region": None,
        "year": None,
        "month": None,
        "product": None,
        "customer": None,
        "status": "paid",
    }

    # ---- Type detection (order is important) ----
    if any(w in q_lower for w in [
        "top-selling product", "top selling product", "best-selling product",
        "best selling product", "highest revenue product", "product with the most revenue",
        "which product generated", "most revenue product", "top product by revenue"
    ]):
        result["type"] = "top_product"

    elif any(w in q_lower for w in [
        "top region", "best region", "region with the most revenue",
        "which region generated", "highest revenue region", "top region by revenue"
    ]):
        result["type"] = "top_region"

    elif any(w in q_lower for w in [
        "top customer", "best customer", "customer with the most revenue",
        "which customer spent", "highest revenue customer", "top customer by revenue"
    ]):
        result["type"] = "top_customer"

    elif any(w in q_lower for w in [
        "how many different customers", "how many unique customers",
        "number of different customers", "number of unique customers",
        "distinct customers", "different customers", "unique customers",
        "how many customers placed", "customers who bought", "customers that bought"
    ]):
        result["type"] = "unique_customers"

    elif any(w in q_lower for w in [
        "how many different products", "how many unique products",
        "number of different products", "number of unique products",
        "distinct products", "unique products"
    ]):
        result["type"] = "unique_products"

    elif any(w in q_lower for w in [
        "total quantity", "total units", "how many units", "total qty", "units sold"
    ]):
        result["type"] = "total_quantity"

    elif any(w in q_lower for w in [
        "count", "how many orders", "number of orders", "how many", "number of"
    ]):
        result["type"] = "count"

    elif any(w in q_lower for w in [
        "average", "avg", "on average", "mean", "worth", "average value",
        "average order", "average paid", "how many us dollars is a"
    ]):
        result["type"] = "average"

    elif "refund" in q_lower:
        result["type"] = "refunds"
        result["status"] = "refunded"

    # ---- Status ----
    if "refund" in q_lower:
        result["status"] = "refunded"
    elif "void" in q_lower:
        result["status"] = "void"
    elif "paid" in q_lower:
        result["status"] = "paid"

    # ---- Region ----
    for r in ["North", "South", "East", "West", "Central"]:
        if r.lower() in q_lower:
            result["region"] = r
            break

    # ---- Year ----
    year_match = re.search(r"\b(20\d{2})\b", q)
    if year_match:
        result["year"] = int(year_match.group(1))

    # ---- Month ----
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4,
        "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }
    for name, num in months.items():
        if name in q_lower:
            result["month"] = num
            break

    # ---- Product ----
    known = get_all_products() | {
        "Mixer", "Blender", "Juicer", "Kettle", "Grinder",
        "Air Fryer", "Toaster", "Rice Cooker", "Coffee Maker",
        "Microwave", "Oven", "Fan", "Heater", "Iron", "Cooker"
    }
    for p in sorted(known, key=len, reverse=True):
        if p.lower() in q_lower:
            result["product"] = p
            break

    # ---- Customer ----
    cust = re.search(r"\b(C\d{4})\b", q, re.IGNORECASE)
    if cust:
        result["customer"] = cust.group(1).upper()

    return result

# ============================================================
# Endpoint
# ============================================================

@app.post("/")
def answer(q: Question):
    parsed = parse_question(q.question)

    kwargs = {
        "region": parsed["region"],
        "year": parsed["year"],
        "month": parsed["month"],
        "product": parsed["product"],
        "customer": parsed["customer"],
        "status": parsed["status"],
    }

    t = parsed["type"]

    if t == "top_product":
        result = get_top_product(**kwargs)
    elif t == "top_region":
        result = get_top_region(**kwargs)
    elif t == "top_customer":
        result = get_top_customer(**kwargs)
    elif t == "unique_customers":
        result = count_unique_customers(**kwargs)
    elif t == "unique_products":
        result = count_unique_products(**kwargs)
    elif t == "total_quantity":
        result = total_quantity(**kwargs)
    elif t == "count":
        result = count_orders(**kwargs)
    elif t == "average":
        result = average_order_value(**kwargs)
    elif t == "refunds":
        result = calculate_revenue(**kwargs)
    else:
        result = calculate_revenue(**kwargs)

    return {"answer": result}

# Health check (optional)
@app.get("/health")
def health():
    return {"status": "ok", "orders_loaded": len(ORDERS)}

@app.get("/debug/average-north")
def debug_avg_north():
    orders = filter_orders(region="North", status="paid")
    total = sum(o["amount_usd"] for o in orders)
    count = len(orders)
    avg = round(total / count, 2) if count else 0
    return {
        "count": count,
        "total": round(total, 2),
        "average": avg,
        "sample": orders[:3] if orders else []
    }