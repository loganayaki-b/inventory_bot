# tools/vendor_tool.py
from typing import Dict
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from database.models import SessionLocal, VendorList

class VendorLookupInput(BaseModel):
    vendor_id: str = Field(..., description="The vendor ID to look up")

class VendorLookupTool(BaseTool):
    name: str = "vendor_lookup"
    description: str = "Find vendor information using vendor ID"
    args_schema: type = VendorLookupInput
    
    def _run(self, vendor_id: str) -> Dict:
        db = SessionLocal()
        try:
            vendor = db.query(VendorList).filter(
                VendorList.vendor_id == vendor_id
            ).first()
            
            if not vendor:
                return {"error": f"Vendor {vendor_id} not found"}
            
            return {
                "vendor_id": vendor.vendor_id,
                "vendor_name": vendor.vendor_name,
                "location": vendor.location,
                "email": vendor.email,
                "contact": vendor.contact
            }
            
        except Exception as e:
            return {"error": str(e)}
        finally:
            db.close()
    
    async def _arun(self, vendor_id: str) -> Dict:
        raise NotImplementedError("Async not implemented")