import sys
from pypdf import PdfReader

def inspect(filename):
    print(f"=== Inspecting {filename} ===")
    try:
        reader = PdfReader(filename)
        print(f"Pages: {len(reader.pages)}")
        for idx, page in enumerate(reader.pages[:5]):
            text = page.extract_text()
            print(f"Page {idx+1} characters: {len(text) if text else 0}")
            if text:
                print(f"Sample: {text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

inspect("luat149.signed.pdf")
inspect("20-btc.pdf")
inspect("luat48.pdf")
