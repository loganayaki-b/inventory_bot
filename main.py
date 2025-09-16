# main.py - Inventory Management System
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys
from pathlib import Path
import os
import io

# Add the backend directory to Python path
sys.path.append(str(Path(__file__).parent / "backend"))

# Import backend modules
try:
    from backend.database.models import init_db, SessionLocal, InventoryData, VendorList
except ImportError as e:
    st.error(f"Database import failed: {e}")
    st.stop()

# Set page configuration
st.set_page_config(
    page_title="Inventory Management System",
    page_icon="📦",
    layout="wide"
)

# Initialize database
@st.cache_resource
def init_database():
    """Initialize the database and return session"""
    try:
        init_db()
        return SessionLocal()
    except Exception as e:
        st.error(f"Database initialization failed: {e}")
        return None

def find_vendor_by_id(db, vendor_id):
    """Find vendor by vendor_id"""
    try:
        vendor = db.query(VendorList).filter(
            VendorList.vendor_id == vendor_id
        ).first()
        
        if vendor:
            return {
                "vendor_id": vendor.vendor_id,
                "vendor_name": vendor.vendor_name,
                "email": vendor.email,
                "contact": vendor.contact,
                "location": vendor.location
            }
        return None
    except Exception as e:
        st.error(f"Error finding vendor: {e}")
        return None

def send_order_email(vendor_data, order_details):
    """Send order email to vendor"""
    try:
        import os
        # Email configuration (prefer env vars if set)
        smtp_server = os.getenv("EMAIL_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("EMAIL_PORT", "465"))  # default SSL port
        sender_email = os.getenv("EMAIL_USERNAME", "loganayakib861@gmail.com")
        sender_password = os.getenv("EMAIL_PASSWORD", "qaez xqxz aron xqta")
        sender_from = os.getenv("EMAIL_FROM", sender_email)
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"Inventory Agent <{sender_from}>"
        msg['To'] = vendor_data['email']
        msg['Subject'] = f"Purchase Order - {order_details['product_name']} ({order_details['product_id']})"
        
        body = f"""
Dear {vendor_data['vendor_name']},

We would like to place an order for the following:

Product: {order_details['product_name']}
Product ID: {order_details['product_id']}
Quantity Needed: {order_details['shortage']} units
Inventory Location: {os.getenv('INVENTORY_LOCATION', 'Chennai')}

Please confirm availability and provide delivery timeline.

Best regards,
Inventory Management System
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email over SSL (more reliable with Gmail/App Password)
        import smtplib
        with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=20) as server:
            server.ehlo()
            server.login(sender_email, sender_password)
            server.sendmail(sender_from, [vendor_data['email']], msg.as_string())
        
        return f"Sent"
    except smtplib.SMTPAuthenticationError as e:
        return f"Error: SMTP auth failed ({e.smtp_code}) {e.smtp_error}"
    except smtplib.SMTPException as e:
        return f"Error: SMTP error {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

def process_uploaded_demand(uploaded_file, db):
    """Process uploaded demand file and compare with inventory"""
    try:
        # Read uploaded file (YOUR INPUT DATA)
        if uploaded_file.name.endswith('.csv'):
            df_demand = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith('.xlsx') or uploaded_file.name.endswith('.xls'):
            df_demand = pd.read_excel(uploaded_file)
        else:
            return None, "Unsupported file format. Please upload CSV or Excel files."
        
        # Get inventory data (YOUR STOCK DATA.XLSX)
        inventory_data = db.query(InventoryData).all()
        
        # Create normalization helpers and indexes
        def _norm(text: str) -> str:
            return str(text or '').strip().lower()
        
        # Indexes for inventory
        name_cat_to_item = {}
        product_id_to_item = {}
        for item in inventory_data:
            name_key = (_norm(item.product_name), _norm(item.category_name))
            name_cat_to_item[name_key] = item
            product_id_to_item[str(item.product_id).strip()] = item
        
        # Aggregate demand across all stores by product (product_name + category)
        agg_rows = {}
        for _, row in df_demand.iterrows():
            product_name = str(row.get('product_name', ''))
            category = str(row.get('Category', ''))
            product_id = str(row.get('product_id', '')).strip()
            demand_qty = int(row.get('demand', 0) or 0)
            key = (_norm(product_name), _norm(category))
            if key not in agg_rows:
                agg_rows[key] = {
                    'product_name': product_name,
                    'category': category,
                    'product_id': product_id,  # keep first seen id as representative
                    'total_demand': 0
                }
            agg_rows[key]['total_demand'] += demand_qty
            # Prefer a non-empty product_id if encountered later
            if product_id and not agg_rows[key]['product_id']:
                agg_rows[key]['product_id'] = product_id
        
        # Evaluate aggregated demand against inventory
        orders_to_send = []
        missing_products = []
        found_products = []  # kept for completeness, not displayed
        
        for key, info in agg_rows.items():
            prod_name_norm, cat_norm = key
            product_name = info['product_name']
            category = info['category']
            product_id = info['product_id']
            total_demand = int(info['total_demand'])
            
            inventory_item = name_cat_to_item.get(key)
            if not inventory_item and product_id:
                inventory_item = product_id_to_item.get(product_id)
            
            if inventory_item:
                current_stock = int(inventory_item.stock or 0)
                shortage = max(0, total_demand - current_stock)
                
                found_products.append({
                    'product_id': product_id or inventory_item.product_id,
                    'category': category or inventory_item.category_name,
                    'product_name': product_name or inventory_item.product_name,
                    'demand': total_demand,
                    'current_stock': current_stock,
                    'shortage': shortage,
                    'status': 'Found in inventory',
                    'vendor_id': inventory_item.vendor_id
                })
                
                if shortage > 0:
                    orders_to_send.append({
                        'store_id': '',  # aggregated across stores
                        'product_id': product_id or inventory_item.product_id,
                        'category': category or inventory_item.category_name,
                        'product_name': product_name or inventory_item.product_name,
                        'current_stock': current_stock,
                        'demand': total_demand,
                        'shortage': shortage,
                        'vendor_id': inventory_item.vendor_id
                    })
            else:
                missing_products.append({
                    'product_id': product_id,
                    'category': category,
                    'product_name': product_name,
                    'demand': total_demand,
                    'current_stock': 0,
                    'shortage': total_demand,
                    'status': 'Not found in inventory',
                    'vendor_id': 'N/A'
                })
                # Consider not-found items as needed, but vendor unknown
                orders_to_send.append({
                    'store_id': '',
                    'product_id': product_id,
                    'category': category,
                    'product_name': product_name,
                    'current_stock': 0,
                    'demand': total_demand,
                    'shortage': total_demand,
                    'vendor_id': ''
                })
        
        # Category-level aggregation (optional): total demand vs stock per category
        demand_by_cat = {}
        stock_by_cat = {}
        cat_display_name = {}
        for key, info in agg_rows.items():
            cat_raw = info['category']
            k = _norm(cat_raw)
            demand_by_cat[k] = demand_by_cat.get(k, 0) + int(info['total_demand'])
            if k not in cat_display_name and cat_raw:
                cat_display_name[k] = cat_raw
        for item in inventory_data:
            k = _norm(item.category_name)
            stock_by_cat[k] = stock_by_cat.get(k, 0) + int(item.stock or 0)
            if k not in cat_display_name and item.category_name:
                cat_display_name[k] = item.category_name
        category_summary = []
        for k in sorted(set(list(demand_by_cat.keys()) + list(stock_by_cat.keys()))):
            td = int(demand_by_cat.get(k, 0))
            ts = int(stock_by_cat.get(k, 0))
            category_summary.append({
                'Category': cat_display_name.get(k, k),
                'Total Demand': td,
                'Total Stock': ts,
                'Shortage': max(0, td - ts)
            })
        
        return {
            'orders_to_send': orders_to_send,
            'missing_products': missing_products,
            'found_products': found_products,
            'category_summary': category_summary,
            'total_processed': len(df_demand)
        }, None
        
    except Exception as e:
        return None, f"Error processing file: {e}"

def send_bulk_orders(db, orders_to_send):
    """Send bulk orders for multiple items"""
    results = []
    
    for order in orders_to_send:
        vendor_data = find_vendor_by_id(db, order['vendor_id'])
        if vendor_data:
            result = send_order_email(vendor_data, order)
            results.append({
                'store_id': order.get('store_id', ''),
                'product_id': order['product_id'],
                'product_name': order['product_name'],
                'shortage': order['shortage'],
                'vendor': vendor_data['vendor_name'],
                'vendor_email': vendor_data['email'],
                'result': result
            })
        else:
            results.append({
                'store_id': order.get('store_id', ''),
                'product_id': order['product_id'],
                'product_name': order['product_name'],
                'shortage': order['shortage'],
                'vendor': 'No vendor found',
                'vendor_email': 'N/A',
                'result': f"Error: No vendor found for vendor_id {order.get('vendor_id', '')}"
            })
    
    return results


def group_orders_by_vendor_product(db, orders_to_send):
    """Group orders to avoid duplicate emails to the same vendor/product. Sum shortages."""
    grouped = {}
    for o in orders_to_send:
        key = (o.get('vendor_id', ''), o.get('product_id', ''))
        if key not in grouped:
            grouped[key] = {
                'vendor_id': o.get('vendor_id', ''),
                'product_id': o.get('product_id', ''),
                'product_name': o.get('product_name', ''),
                'category': o.get('category', ''),
                'current_stock': int(o.get('current_stock', 0) or 0),
                'demand': int(o.get('demand', 0) or 0),
                'shortage': int(o.get('shortage', 0) or 0),
            }
        else:
            grouped[key]['demand'] += int(o.get('demand', 0) or 0)
            grouped[key]['shortage'] += int(o.get('shortage', 0) or 0)
            # keep minimal stock for info
            grouped[key]['current_stock'] = min(grouped[key]['current_stock'], int(o.get('current_stock', 0) or 0))
    
    # Enrich with vendor name/email
    consolidated = []
    for (_, _), g in grouped.items():
        vendor = find_vendor_by_id(db, g['vendor_id']) if g['vendor_id'] else None
        consolidated.append({
            **g,
            'vendor': vendor['vendor_name'] if vendor else 'No vendor found',
            'vendor_email': vendor['email'] if vendor else 'N/A',
        })
    return consolidated


def send_bulk_orders_grouped(db, grouped_orders):
    """Send one email per (vendor_id, product_id) with consolidated shortage."""
    results = []
    for go in grouped_orders:
        if not go.get('vendor_id'):
            results.append({
                'product_id': go['product_id'],
                'product_name': go['product_name'],
                'shortage': go['shortage'],
                'vendor': 'No vendor found',
                'vendor_email': 'N/A',
                'result': 'Error: Missing vendor_id'
            })
            continue
        vendor = find_vendor_by_id(db, go['vendor_id'])
        if not vendor:
            results.append({
                'product_id': go['product_id'],
                'product_name': go['product_name'],
                'shortage': go['shortage'],
                'vendor': 'No vendor found',
                'vendor_email': 'N/A',
                'result': f"Error: No vendor found for vendor_id {go['vendor_id']}"
            })
            continue
        order_payload = {
            'store_id': '',
            'product_id': go['product_id'],
            'category': go.get('category', ''),
            'product_name': go['product_name'],
            'current_stock': go.get('current_stock', 0),
            'demand': go.get('demand', 0),
            'shortage': go.get('shortage', 0),
            'vendor_id': go['vendor_id'],
        }
        result_msg = send_order_email(vendor, order_payload)
        results.append({
            'product_id': go['product_id'],
            'product_name': go['product_name'],
            'shortage': go['shortage'],
            'vendor': vendor['vendor_name'],
            'vendor_email': vendor['email'],
            'result': result_msg
        })
    return results

# Main application
def main():
    # Initialize database
    db = init_database()
    if db is None:
        st.error("Failed to initialize database. Please check your configuration.")
        return
    
    # App title
    st.title("📦 Inventory Management System")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("Navigation")
        page = st.radio("Go to", ["File Upload", "Inventory"])
        
        # Database status
        if db:
            st.success("✅ Database Connected")
        else:
            st.error("❌ Database Disconnected")
        
        # Sidebar no longer renders inventory directly; use Inventory page
    
    # File Upload Page
    if page == "File Upload":
        st.header("📁 Upload Your Demand Data")
        
        st.info("Upload your demand data file. The system will check it against the inventory data (stock data.xlsx) and send emails to vendors for products that need restocking.")
        
        # File upload
        uploaded_file = st.file_uploader(
            "Choose your demand data file",
            type=['csv', 'xlsx', 'xls'],
            help="Upload your demand data with columns: store_id, product_id, Category, product_name, demand"
        )
        
        if uploaded_file is not None:
            st.success(f"Your demand file uploaded: {uploaded_file.name}")
            
            # Show complete uploaded file
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_uploaded = pd.read_csv(uploaded_file)
                else:
                    df_uploaded = pd.read_excel(uploaded_file)
                
                st.subheader(f"Your Complete Uploaded File: {uploaded_file.name}")
                st.dataframe(df_uploaded, width='stretch')
                
                # Show file info
                st.info(f"Total rows in your file: {len(df_uploaded)}")
                
                # Process demand file
                if st.button("Check Demand Against Inventory", type="primary"):
                    with st.spinner("Checking your demand data against inventory..."):
                        result, error = process_uploaded_demand(uploaded_file, db)
                        
                        if error:
                            st.error(error)
                        else:
                            # Save to session so content persists after further actions
                            st.session_state['last_result'] = result
                            # Precompute inventory df for display and persist
                            inventory_data = db.query(InventoryData).all()
                            st.session_state['inventory_df'] = pd.DataFrame([{
                                "Product ID": item.product_id,
                                "Category": item.category_name,
                                "Product Name": item.product_name,
                                "Vendor ID": item.vendor_id,
                                "Current Stock": item.stock
                            } for item in inventory_data])
                            
                            # Also prepare grouped preview and persist
                            grouped_preview = group_orders_by_vendor_product(db, result['orders_to_send'])
                            st.session_state['grouped_preview'] = grouped_preview
                            # Removed completion banner per requirement
                
                # Render from session if available (keeps all sections visible)
                if 'last_result' in st.session_state:
                    result = st.session_state['last_result']
                    
                    # Removed navigation hint per requirement
                    
                    # Category summary hidden per requirement
                    
                    # (Removed) Products Found in Inventory table per requirement
                    
                    # Show missing products
                    if result['missing_products']:
                        st.subheader(f"❌ Products NOT Found in Inventory ({len(result['missing_products'])} products)")
                        missing_df = pd.DataFrame(result['missing_products'])
                        st.dataframe(missing_df, width='stretch')
                    
                    # Products That Need Restocking table removed; continue with email plan if any
                    if result['orders_to_send']:
                        grouped_preview = st.session_state.get('grouped_preview') or group_orders_by_vendor_product(db, result['orders_to_send'])
                        st.subheader("📧 Planned Vendor Emails (grouped by vendor and product)")
                        preview_df = pd.DataFrame(grouped_preview)
                        st.dataframe(preview_df, width='stretch')
                        st.subheader("Send Purchase Orders to Vendors")
                        if st.button(f"Send {len(grouped_preview)} Emails", type="primary"):
                            with st.spinner("Sending purchase orders..."):
                                order_results = send_bulk_orders_grouped(db, grouped_preview)
                                st.session_state['order_results'] = order_results
                        
                        # Always show results if present
                        if 'order_results' in st.session_state:
                            order_results = st.session_state['order_results']
                            # Summary table of all emails attempted
                            st.subheader("Email Attempts Summary")
                            summary_df = pd.DataFrame(order_results)
                            st.dataframe(summary_df, width='stretch')
                         
                    if not result['orders_to_send'] and not result['missing_products']:
                        st.success("✅ All products in your demand have sufficient stock in inventory!")
                     
                    st.info(f"Total items from your demand processed: {result['total_processed']}")
             
            except Exception as e:
                st.error(f"Error reading file: {e}")
    elif page == "Inventory":
        st.header("📦 Inventory List")
        try:
            inventory_df = st.session_state.get('inventory_df')
            if inventory_df is None or inventory_df.empty:
                inventory_data = db.query(InventoryData).all()
                # join vendor name/email
                vendors = {v.vendor_id: v for v in db.query(VendorList).all()}
                records = []
                for item in inventory_data:
                    v = vendors.get(item.vendor_id)
                    records.append({
                        "Product ID": item.product_id,
                        "Category": item.category_name,
                        "Product Name": item.product_name,
                        "Vendor ID": item.vendor_id,
                        "Vendor Name": getattr(v, 'vendor_name', ''),
                        "Vendor Email": getattr(v, 'email', ''),
                        "Current Stock": item.stock
                    })
                inventory_df = pd.DataFrame(records)
                st.session_state['inventory_df'] = inventory_df
            st.dataframe(inventory_df, width='stretch')
            # Optional download
            csv_inv = inventory_df.to_csv(index=False)
            st.download_button(
                label="Download Inventory CSV",
                data=csv_inv,
                file_name="inventory_export.csv",
                mime="text/csv"
            )
        except Exception as e:
            st.error(f"Failed to load inventory: {e}")
    
    # AI Assistant Page
    else:  # AI Assistant
        st.header("🤖 AI Assistant")
        
        st.info("Ask about inventory or upload a demand file here to process it directly.")
        
        # Chat interface
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Chat input
        if prompt := st.chat_input("Ask about inventory management..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    # Auto-process if a file was uploaded in assistant and not yet processed
                    ai_response = "You can upload a demand file below to process against inventory and send vendor emails."
                    if 'ai_uploaded_file_buffer' in st.session_state and st.session_state['ai_uploaded_file_buffer'] is not None:
                        result, error = process_uploaded_demand(st.session_state['ai_uploaded_file_buffer'], db)
                        if error:
                            ai_response += f"\n\nProcessing error: {error}"
                        else:
                            st.session_state['last_result'] = result
                            inventory_data = db.query(InventoryData).all()
                            st.session_state['inventory_df'] = pd.DataFrame([{
                                "Product ID": item.product_id,
                                "Category": item.category_name,
                                "Product Name": item.product_name,
                                "Vendor ID": item.vendor_id,
                                "Current Stock": item.stock
                            } for item in inventory_data])
                            st.session_state['grouped_preview'] = group_orders_by_vendor_product(db, result['orders_to_send'])
                            ai_response += "\n\nYour uploaded file has been processed. See results below."
                    st.markdown(ai_response)
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})
        
        st.markdown("---")
        st.subheader("➕ Upload Demand File (within Assistant)")
        ai_uploaded_file = st.file_uploader(
            "Choose demand file (CSV/XLS/XLSX)",
            type=["csv", "xlsx", "xls"],
            key="ai_uploader",
            help="Columns: store_id, product_id, Category, product_name, demand"
        )
        
        if ai_uploaded_file is not None:
            try:
                if ai_uploaded_file.name.endswith('.csv'):
                    ai_df_uploaded = pd.read_csv(ai_uploaded_file)
                else:
                    ai_df_uploaded = pd.read_excel(ai_uploaded_file)
                st.success(f"Uploaded: {ai_uploaded_file.name}")
                st.dataframe(ai_df_uploaded, width='stretch')
                st.info(f"Total rows: {len(ai_df_uploaded)}")
                # Keep a buffer in session so chat can auto-process on next message
                st.session_state['ai_uploaded_file_buffer'] = ai_uploaded_file
                
                if st.button("Process in Assistant", type="primary"):
                    with st.spinner("Processing against inventory..."):
                        result, error = process_uploaded_demand(ai_uploaded_file, db)
                        if error:
                            st.error(error)
                        else:
                            st.session_state['last_result'] = result
                            inventory_data = db.query(InventoryData).all()
                            st.session_state['inventory_df'] = pd.DataFrame([{
                                "Product ID": item.product_id,
                                "Category": item.category_name,
                                "Product Name": item.product_name,
                                "Vendor ID": item.vendor_id,
                                "Current Stock": item.stock
                            } for item in inventory_data])
                            st.session_state['grouped_preview'] = group_orders_by_vendor_product(db, result['orders_to_send'])
                            st.success("Comparison complete. See results below.")
            except Exception as e:
                st.error(f"Error reading file: {e}")
        
        # Render results if present (same as File Upload flow)
        if 'last_result' in st.session_state:
            result = st.session_state['last_result']
            
            # Missing products
            if result['missing_products']:
                st.subheader(f"❌ Products NOT Found in Inventory ({len(result['missing_products'])} products)")
                missing_df = pd.DataFrame(result['missing_products'])
                st.dataframe(missing_df, width='stretch')
            
            # Products That Need Restocking table removed; proceed with email plan if any
            if result['orders_to_send']:
                grouped_preview = st.session_state.get('grouped_preview') or group_orders_by_vendor_product(db, result['orders_to_send'])
                st.subheader("📧 Planned Vendor Emails (grouped by vendor and product)")
                preview_df = pd.DataFrame(grouped_preview)
                st.dataframe(preview_df, width='stretch')
                st.subheader("Send Purchase Orders to Vendors")
                if st.button(f"Send {len(grouped_preview)} Emails", type="primary", key="ai_send"):
                    with st.spinner("Sending purchase orders..."):
                        order_results = send_bulk_orders_grouped(db, grouped_preview)
                        st.session_state['order_results'] = order_results
                if 'order_results' in st.session_state:
                    order_results = st.session_state['order_results']
                    st.subheader("Email Attempts Summary")
                    summary_df = pd.DataFrame(order_results)
                    st.dataframe(summary_df, width='stretch')
            
            if not result['orders_to_send'] and not result['missing_products']:
                st.success("✅ All products have sufficient stock.")

if __name__ == "__main__":
    main()