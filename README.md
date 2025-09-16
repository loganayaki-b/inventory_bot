# Inventory Management System

A Streamlit-based tool to compare demand files against inventory, identify shortages, and send purchase order emails to vendors.

## Features
- Upload CSV/XLSX demand files and aggregate demand by product
- Compare demand against the inventory database
- Generate a consolidated list of shortages
- Group purchase orders per vendor and send emails
- Simple, local SQLite database initialized on first run

## Requirements
- Python 3.10+
- Windows (tested) or any OS supported by Streamlit and Python

## Quick Start
1. Create and activate a virtual environment
   - Windows (cmd):
     ```bat
     python -m venv venv
     venv\Scripts\activate
     ```
2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables
   - Copy the example file and edit your secrets locally:
     ```bat
     copy .env.example .env
     ```
   - Open `.env` and set values:
     ```env
     API_HOST=127.0.0.1
     API_PORT=8000
     DEBUG=true
     APP_NAME=Inventory Forecasting System

     GEMINI_API_KEY=
     GEMINI_MODEL_NAME=gemini-2.0-flash-exp

     EMAIL_HOST=smtp.gmail.com
     EMAIL_PORT=587
     EMAIL_USERNAME=your_email@gmail.com
     EMAIL_PASSWORD=your_app_password
     EMAIL_FROM=your_email@gmail.com
     ```
   - Note: `.env` is ignored by Git. Do not commit real secrets. Share `.env.example` instead.
4. Run the app
   ```bash
   streamlit run main.py
   ```
   - Or with the bundled venv explicitly:
     ```bat
     venv\Scripts\python -m streamlit run main.py --server.address 127.0.0.1 --server.port 8501
     ```
   - Open: http://127.0.0.1:8501

## Using the App
- Go to "File Upload" → upload your demand CSV/XLSX (columns: `store_id, product_id, Category, product_name, demand`).
- Click "Check Demand Against Inventory" to compute shortages.
- Review the grouped vendor emails and click "Send X Emails" to dispatch purchase orders.

## Sample Files
- `sample_demand.csv` – example demand file
- `sample_requirements.csv` – simple product/quantity list

## Environment Variables
These are read from `.env` via `python-dotenv`:
- `API_HOST`, `API_PORT`, `DEBUG`, `APP_NAME`
- `GEMINI_API_KEY`, `GEMINI_MODEL_NAME`
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USERNAME`, `EMAIL_PASSWORD`, `EMAIL_FROM`

## Project Structure (high level)
- `main.py` – Streamlit UI and processing flow
- `backend/` – agents, tools, database, and API routes
- `config/settings.py` – loads configuration from `.env`
- `backend/data/` – local Excel data (ignored by Git)

## Security Notes
- Rotate any keys that were previously hardcoded.
- Keep `.env` local. The `.gitignore` prevents committing it; share `.env.example` only.

## Troubleshooting
- Port already in use: run Streamlit with `--server.port 8502` (or another free port).
- Email errors: ensure you use an app password and correct SMTP port (587 for TLS or 465 for SSL, depending on your provider).
- Dependency issues: re-run `pip install -r requirements.txt` inside the virtual environment.
