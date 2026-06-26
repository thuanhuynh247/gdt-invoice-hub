import os
import sys

# Add root folder to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import fitz # PyMuPDF
except ImportError:
    print("Error: PyMuPDF is not installed. Run 'uv pip install PyMuPDF'")
    sys.exit(1)

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_FILES = ["luat48.pdf", "luat149.signed.pdf", "20-btc.pdf", "thongtu18_2026.pdf", "thongtu69_2025.pdf", "nghidinh144_2026.pdf"]
OUTPUT_DIR = os.path.join(WORKSPACE_DIR, "static", "tax_pages")

def render_pdfs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Saving rendered PDF pages to: {OUTPUT_DIR}")
    
    for pdf_name in PDF_FILES:
        pdf_path = os.path.join(WORKSPACE_DIR, pdf_name)
        if not os.path.exists(pdf_path):
            print(f"Skipping {pdf_name} (File not found)")
            continue
            
        print(f"Rendering {pdf_name}...")
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                # Render to pixmap with 150 DPI for legibility and small file size
                zoom = 150 / 72
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                
                out_name = f"{os.path.splitext(pdf_name)[0]}_page_{page_num + 1}.png"
                out_path = os.path.join(OUTPUT_DIR, out_name)
                pix.save(out_path)
                print(f"  -> Saved page {page_num + 1} to {out_name}")
            doc.close()
        except Exception as e:
            print(f"Error rendering {pdf_name}: {e}")

if __name__ == "__main__":
    render_pdfs()
