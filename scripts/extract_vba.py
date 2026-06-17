import sys
import os
from oletools.olevba import VBA_Parser

def main():
    xl_path = r"D:\LearnAnyThing\Hoa Don VBA\TaiHoaDonDienTu_v6.1_luuUserPass_GPE.xlsm"
    try:
        parser = VBA_Parser(xl_path)
        print("VBA Macros detected:", parser.detect_vba_macros())
        
        for vba_filename, stream_path, vba_filename_in_zip, code in parser.extract_macros():
            # Clean stream path to make a safe filename
            clean_name = stream_path.replace("/", "_").replace("\\", "_")
            print("="*60)
            print(f"Module: {vba_filename} | Stream: {stream_path} -> Clean Name: {clean_name}")
            print("="*60)
            
            # Save the code to a file for analysis
            out_name = f"scripts/vba_{clean_name}.txt"
            with open(out_name, "w", encoding="utf-8") as f:
                f.write(code)
            print(f"Saved to {out_name} ({len(code)} chars)")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
