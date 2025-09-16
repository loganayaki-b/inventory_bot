# api/routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from database.connection import get_db
from database.models import ProductCatalogue, VendorList, InputData
from pydantic import BaseModel
from typing import Dict, Any
from agents.workflow_agent import create_workflow_agent

router = APIRouter(prefix="/api", tags=["inventory"])

class ProductRequest(BaseModel):
    product_identifier: str  # Can be product_id or product_name

class ProductIDRequest(BaseModel):
    product_id: str

class OrderRequest(BaseModel):
    vendor_email: str
    vendor_name: str
    product_name: str
    quantity: int
    product_id: str

@router.post("/analyze-inventory")
def analyze_inventory(request: ProductIDRequest, db: Session = Depends(get_db)):
    """Analyze inventory for a specific product"""
    try:
        # Get product from catalogue
        product = db.query(ProductCatalogue).filter(
            ProductCatalogue.product_id == request.product_id
        ).first()
        
        if not product:
            raise HTTPException(status_code=404, detail=f"Product '{request.product_id}' not found")
        
        # Calculate total demand
        total_demand = db.query(func.sum(InputData.demand)).filter(
            InputData.product_id == product.product_id
        ).scalar() or 0
        
        # Current stock
        current_stock = product.stock
        
        # Calculate required stock
        required_stock = max(0, total_demand - current_stock)
        
        return {
            "product_id": product.product_id,
            "product_name": product.product_name,
            "category_name": product.category_name,
            "current_stock": current_stock,
            "total_demand": total_demand,
            "required_stock": required_stock,
            "status": "reorder_needed" if required_stock > 0 else "sufficient_stock"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/find-vendor")
def find_vendor(request: ProductIDRequest, db: Session = Depends(get_db)):
    """Find vendor for a specific product"""
    try:
        # Get product from catalogue
        product = db.query(ProductCatalogue).filter(
            ProductCatalogue.product_id == request.product_id
        ).first()
        
        if not product:
            raise HTTPException(status_code=404, detail=f"Product '{request.product_id}' not found")
        
        # Get vendor details
        vendor = db.query(VendorList).filter(
            VendorList.vendor_id == product.vendor_id
        ).first()
        
        if not vendor:
            raise HTTPException(status_code=404, detail=f"Vendor {product.vendor_id} not found")
        
        # Calculate required stock for additional context
        total_demand = db.query(func.sum(InputData.demand)).filter(
            InputData.product_id == product.product_id
        ).scalar() or 0
        required_stock = max(0, total_demand - product.stock)
        
        return {
            "vendor_id": vendor.vendor_id,
            "vendor_name": vendor.vendor_name,
            "location": vendor.location,
            "email": vendor.email,
            "contact": vendor.contact,
            "product_id": product.product_id,
            "product_name": product.product_name,
            "required_stock": required_stock
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send-order")
def send_order(request: OrderRequest):
    """Send order to vendor using email agent"""
    try:
        # Create workflow agent
        agent = create_workflow_agent()
        
        # Use agent to send email
        query = f"Send order email to {request.vendor_name} at {request.vendor_email} for {request.quantity} units of {request.product_name} (ID: {request.product_id})"
        result = agent.invoke({"input": query})
        
        return {
            "message": f"Order request sent to {request.vendor_name}",
            "details": result
        }
        
    except Exception as e:
        return {"message": f"Failed to send order: {str(e)}"}

@router.get("/dashboard-data")
def get_dashboard_data(db: Session = Depends(get_db)):
    """Get dashboard data including products needing reorder"""
    try:
        # Get all products
        products = db.query(ProductCatalogue).all()
        total_products = len(products)
        
        reorder_products = []
        
        for product in products:
            # Calculate total demand for this product
            total_demand = db.query(func.sum(InputData.demand)).filter(
                InputData.product_id == product.product_id
            ).scalar() or 0
            
            required_stock = max(0, total_demand - product.stock)
            
            if required_stock > 0:
                reorder_products.append({
                    "product_id": product.product_id,
                    "product_name": product.product_name,
                    "current_stock": product.stock,
                    "total_demand": total_demand,
                    "required_stock": required_stock
                })
        
        return {
            "total_products": total_products,
            "reorder_count": len(reorder_products),
            "reorder_products": reorder_products
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/products")
def get_all_products(db: Session = Depends(get_db)):
    """Get all products from catalogue"""
    try:
        products = db.query(ProductCatalogue).all()
        return {
            "status": "success",
            "data": [
                {
                    "product_id": p.product_id,
                    "product_name": p.product_name,
                    "category_name": p.category_name
                }
                for p in products
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agent-workflow")
def run_agent_workflow(request: ProductRequest):
    """Run the complete agent workflow for inventory management"""
    try:
        # Create workflow agent
        agent = create_workflow_agent()
        
        # Run the workflow
        query = f"Analyze inventory and check if reordering is needed for product: {request.product_identifier}"
        result = agent.invoke({"input": query})
        
        return {
            "status": "success",
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))