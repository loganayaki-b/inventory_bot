# tools/inventory_tool.py
from typing import Dict, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from database.models import SessionLocal, InventoryData


def _normalize(text: str) -> str:
    return (text or "").strip().lower()


class StockAnalysisInput(BaseModel):
    product_name: str = Field(..., description="Product name to analyze")
    category: str = Field(..., description="Category name for the product")
    demand: int = Field(..., description="Demand quantity to compare against stock")
    product_id: Optional[str] = Field(None, description="Optional product ID for fallback matching")


class StockAnalysisTool(BaseTool):
    name: str = "stock_analysis"
    description: str = (
        "Analyze inventory stock levels for a given product (matched by product_name and category) "
        "and calculate required stock based on provided demand. Case-insensitive, trimmed matching."
    )
    args_schema: type = StockAnalysisInput

    def _run(self, product_name: str, category: str, demand: int, product_id: Optional[str] = None) -> Dict:
        db = SessionLocal()
        try:
            normalized_key = (_normalize(product_name), _normalize(category))

            # Load inventory and build lookup
            inventory = db.query(InventoryData).all()
            key_to_item = {(_normalize(i.product_name), _normalize(i.category_name)): i for i in inventory}

            matched_item = key_to_item.get(normalized_key)

            # Fallback: try by product_id if provided and not matched by name/category
            if not matched_item and product_id:
                product_id_norm = (product_id or "").strip()
                matched_item = next((i for i in inventory if (i.product_id or "").strip() == product_id_norm), None)

            if not matched_item:
                return {
                    "status": "not_found",
                    "message": "Product not found in inventory",
                    "product_name": product_name,
                    "category": category,
                    "product_id": product_id or "",
                    "demand": int(demand),
                }

            current_stock = int(matched_item.stock or 0)
            required_stock = max(0, int(demand) - current_stock)

            return {
                "status": "reorder_needed" if required_stock > 0 else "sufficient_stock",
                "product_id": matched_item.product_id,
                "product_name": matched_item.product_name,
                "category_name": matched_item.category_name,
                "current_stock": current_stock,
                "demand": int(demand),
                "required_stock": required_stock,
                "vendor_id": matched_item.vendor_id,
            }

        except Exception as e:
            return {"error": str(e)}
        finally:
            db.close()

    async def _arun(self, product_name: str, category: str, demand: int, product_id: Optional[str] = None) -> Dict:
        raise NotImplementedError("Async not implemented")