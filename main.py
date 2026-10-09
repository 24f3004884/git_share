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

def calculate_revenue(
    region: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    product: Optional[str] = None,
    customer: Optional[str] = None,
    status: str = "paid",
) -> float:
    total = 0.0
    for o in ORDERS:
        if o["status"] != status:
            continue
        if region and o["region"].lower() != region.lower():
            continue
        if product and o["product"].lower() != product.lower():
            continue
        if customer and o["customer"].lower() != customer.lower():
            continue
        if year and o["created_kolkata"].year != year:
            continue
        if month and o["created_kolkata"].month != month:
            continue
        total += o["amount_usd"]
    return round(total, 2)

def get_top_product(
    year: Optional[int] = None,
    month: Optional[int] = None,
    region: Optional[str] = None,
) -> str:
    """Return the product name with highest revenue."""
    from collections import defaultdict
    revenue_by_product = defaultdict(float)

    for o in ORDERS:
        if o["status"] != "paid":
            continue
        if region and o["region"].lower() != region.lower():
            continue
        if year and o["created_kolkata"].year != year:
            continue
        if month and o["created_kolkata"].month != month:
            continue
        revenue_by_product[o["product"]] += o["amount_usd"]

    if not revenue_by_product:
        return "None"

    # Return the product with the highest revenue
    top = max(revenue_by_product.items(), key=lambda x: x[1])
    return top[0]   # product name

# ---------- Simple English → filters parser ----------
def parse_question(q: str) -> dict:
    q_lower = q.lower()
    result = {
        "type": "revenue",          # revenue | refunds | top_product
        "region": None,
        "year": None,
        "month": None,
        "product": None,
        "customer": None,
    }

    # Detect question type
    if "top-selling" in q_lower or "top selling" in q_lower or "best-selling" in q_lower or "highest revenue" in q_lower and "product" in q_lower:
        result["type"] = "top_product"
    elif "refund" in q_lower:
        result["type"] = "refunds"

    # Region
    for r in ["North", "South", "East", "West", "Central"]:
        if r.lower() in q_lower:
            result["region"] = r
            break

    # Year
    year_match = re.search(r"\b(20\d{2})\b", q)
    if year_match:
        result["year"] = int(year_match.group(1))

    # Month
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

    # Product
    products = ["Mixer", "Blender", "Juicer", "Kettle", "Grinder", "Air Fryer", "Toaster"]
    for p in products:
        if p.lower() in q_lower:
            result["product"] = p
            break

    # Customer
    cust_match = re.search(r"\b(C\d{4})\b", q, re.IGNORECASE)
    if cust_match:
        result["customer"] = cust_match.group(1).upper()

    return result

# ---------- Main endpoint ----------
@app.post("/")
def answer(q: Question):
    parsed = parse_question(q.question)

    if parsed["type"] == "top_product":
        result = get_top_product(
            year=parsed["year"],
            month=parsed["month"],
            region=parsed["region"]
        )
    elif parsed["type"] == "refunds":
        result = calculate_revenue(
            region=parsed["region"],
            year=parsed["year"],
            month=parsed["month"],
            product=parsed["product"],
            customer=parsed["customer"],
            status="refunded"
        )
    else:  # revenue
        result = calculate_revenue(
            region=parsed["region"],
            year=parsed["year"],
            month=parsed["month"],
            product=parsed["product"],
            customer=parsed["customer"],
            status="paid"
        )

    return {"answer": result}
'''from fastapi import FastAPI
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

# ---------- Helper: calculate revenue / refunds ----------
def calculate(
    metric: str = "revenue",
    region: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    product: Optional[str] = None,
    customer: Optional[str] = None,
) -> float:
    total = 0.0
    target_status = "paid" if metric == "revenue" else "refunded"

    for o in ORDERS:
        if o["status"] != target_status:
            continue
        if region and o["region"].lower() != region.lower():
            continue
        if product and o["product"].lower() != product.lower():
            continue
        if customer and o["customer"].lower() != customer.lower():
            continue
        if year and o["created_kolkata"].year != year:
            continue
        if month and o["created_kolkata"].month != month:
            continue
        total += o["amount_usd"]

    return round(total, 2)

# ---------- Simple English → filters parser ----------
def parse_question(q: str) -> dict:
    q_lower = q.lower()
    result = {
        "metric": "revenue",
        "region": None,
        "year": None,
        "month": None,
        "product": None,
        "customer": None,
    }

    # Metric
    if "refund" in q_lower:
        result["metric"] = "refunds"

    # Region
    for r in ["North", "South", "East", "West", "Central"]:
        if r.lower() in q_lower:
            result["region"] = r
            break

    # Year
    year_match = re.search(r"\b(20\d{2})\b", q)
    if year_match:
        result["year"] = int(year_match.group(1))

    # Month
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

    # Product (common ones from the data)
    products = ["Mixer", "Blender", "Juicer", "Kettle", "Grinder", "Air Fryer", "Toaster"]
    for p in products:
        if p.lower() in q_lower:
            result["product"] = p
            break

    # Customer (Cxxxx)
    cust_match = re.search(r"\b(C\d{4})\b", q, re.IGNORECASE)
    if cust_match:
        result["customer"] = cust_match.group(1).upper()

    return result

# ---------- Main endpoint ----------
@app.post("/")
def answer(q: Question):
    parsed = parse_question(q.question)
    value = calculate(**parsed)
    return {"answer": value}'''

# Health check (optional)
@app.get("/health")
def health():
    return {"status": "ok", "orders_loaded": len(ORDERS)}