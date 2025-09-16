# tools/email_tool.py
from typing import Dict
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys
from pathlib import Path

# Add the parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import settings

class SendOrderEmailInput(BaseModel):
    vendor_email: str = Field(..., description="Vendor's email address")
    vendor_name: str = Field(..., description="Vendor's name")
    product_name: str = Field(..., description="Product name to order")
    quantity: int = Field(..., description="Quantity to order")
    product_id: str = Field(..., description="Product ID")

class SendOrderEmailTool(BaseTool):
    name: str = "send_order_email"
    description: str = "Send purchase order email to vendor"
    args_schema: type = SendOrderEmailInput
    
    def _run(self, vendor_email: str, vendor_name: str, product_name: str, 
             quantity: int, product_id: str) -> Dict:
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = settings.EMAIL_FROM
            msg['To'] = vendor_email
            msg['Subject'] = f"Purchase Order - {product_name} ({product_id})"
            
            # Email body
            body = f"""
            Dear {vendor_name},
            
            We would like to place an order for the following item:
            
            Product: {product_name}
            Product ID: {product_id}
            Quantity: {quantity}
            
            Please confirm availability and provide delivery timeline.
            
            Best regards,
            Inventory Management System
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Connect to SMTP server and send email
            server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
            server.starttls()
            server.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
            text = msg.as_string()
            server.sendmail(settings.EMAIL_FROM, vendor_email, text)
            server.quit()
            
            return {
                "status": "success",
                "message": f"Order email sent to {vendor_name} at {vendor_email}"
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Failed to send email: {str(e)}"
            }
    
    async def _arun(self, vendor_email: str, vendor_name: str, product_name: str, 
                   quantity: int, product_id: str) -> Dict:
        raise NotImplementedError("Async not implemented")