from app import create_app
from invoices.ai_service import run_dynamic_pdf_ingestion

if __name__ == "__main__":
    app = create_app()
    print("Starting manual PDF ingestion...")
    run_dynamic_pdf_ingestion(app)
    print("Finished manual PDF ingestion.")
