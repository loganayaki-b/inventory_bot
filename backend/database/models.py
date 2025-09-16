# database/models.py
from sqlalchemy import Column, Integer, String, Float, create_engine, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import pandas as pd
import sys
from pathlib import Path

# Add the parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import settings

Base = declarative_base()

class InventoryData(Base):
    __tablename__ = "inventory_data"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String, index=True)
    category_name = Column(String)
    product_name = Column(String)
    vendor_id = Column(String)
    stock = Column(Integer)

class VendorList(Base):
    __tablename__ = "vendor_list"
    
    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(String, index=True)
    vendor_name = Column(String)
    location = Column(String)
    email = Column(String)
    contact = Column(String)

# Database setup
DATABASE_URL = f"sqlite:///{settings.BASE_DIR}/inventory.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database and load data from Excel files"""
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Clear existing data
    db.query(InventoryData).delete()
    db.query(VendorList).delete()
    
    # Load data from Excel files
    try:
        # Load Stock Data (Inventory Dataset)
        df_stock = pd.read_excel(settings.BASE_DIR / "backend" / "data" / "stock data.xlsx")
        for _, row in df_stock.iterrows():
            inventory = InventoryData(
                product_id=row['product_id'],
                category_name=row['Category_name'],
                product_name=row['product_name'],
                vendor_id=row['vendor_id'],
                stock=row['stock']
            )
            db.add(inventory)
        
        # Load Vendor Data
        df_vendor = pd.read_excel(settings.BASE_DIR / "backend" / "data" / "vendor data.xlsx")
        for _, row in df_vendor.iterrows():
            vendor = VendorList(
                vendor_id=row['vendor_id'],
                vendor_name=row['vendor_name'],
                location=row['Location'],
                email=row['email'],
                contact=row['contact']
            )
            db.add(vendor)
        
        db.commit()
        print("Database initialized successfully with inventory and vendor data!")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()