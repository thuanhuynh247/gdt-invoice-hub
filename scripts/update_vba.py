import os
import sys
import win32com.client

def main():
    xl_path = r"D:\LearnAnyThing\Hoa Don VBA\TaiHoaDonDienTu_v6.2.xlsm"
    bas_login = r"D:\LearnAnyThing\Hoa Don VBA\vba_modules\modSmartInvoiceLogin.bas"
    frm_login = r"D:\LearnAnyThing\Hoa Don VBA\vba_modules\frmDangNhap.bas"

    if not os.path.exists(xl_path):
        print(f"Error: Excel file not found at {xl_path}")
        sys.exit(1)
        
    print("Initializing Excel...")
    excel = win32com.client.Dispatch("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False

    try:
        print(f"Opening workbook: {xl_path}")
        wb = excel.Workbooks.Open(xl_path)
        
        # Access VBA project
        try:
            vbp = wb.VBProject
        except Exception as e:
            print("Error: Trust Center access to VBA Project Object Model is not enabled.")
            print("Please enable it in Excel under Options -> Trust Center -> Trust Center Settings -> Macro Settings -> Trust access to the VBA project object model.")
            print(f"Error details: {e}")
            wb.Close(SaveChanges=False)
            excel.Quit()
            sys.exit(1)

        components = vbp.VBComponents
        
        # 1. Update/Import modSmartInvoiceLogin (Standard Module)
        # Check if modSmartInvoiceLogin already exists, remove it if it does
        try:
            comp = components("modSmartInvoiceLogin")
            components.Remove(comp)
            print("Removed existing modSmartInvoiceLogin component.")
        except Exception:
            pass
            
        print(f"Importing standard module: {bas_login}")
        components.Import(bas_login)
        print("Successfully imported modSmartInvoiceLogin.")
        
        # 2. Update frmDangNhap code (UserForm)
        # Instead of importing (which would fail or create a standard module), we update its CodeModule directly.
        try:
            comp_frm = components("frmDangNhap")
            print("Found frmDangNhap UserForm. Updating code module...")
            
            # Read frmDangNhap.bas and strip Attribute lines
            with open(frm_login, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                
            code_lines = []
            for line in lines:
                if line.strip().startswith("Attribute "):
                    continue
                code_lines.append(line)
                
            new_code = "".join(code_lines)
            
            # Clear old code and write new code
            code_module = comp_frm.CodeModule
            count = code_module.CountOfLines
            if count > 0:
                code_module.DeleteLines(1, count)
                
            code_module.AddFromString(new_code)
            print("Successfully updated frmDangNhap code module.")
            
        except Exception as e:
            print(f"Error updating frmDangNhap: {e}")
            wb.Close(SaveChanges=False)
            excel.Quit()
            sys.exit(1)
            
        # Save and close
        print("Saving workbook...")
        wb.Save()
        wb.Close(SaveChanges=True)
        print("Excel VBA update completed successfully!")
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        try:
            wb.Close(SaveChanges=False)
        except Exception:
            pass
    finally:
        excel.Quit()

if __name__ == "__main__":
    main()
