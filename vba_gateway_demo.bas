Attribute VB_Name = "modWebappGatewayIntegration"
' ==============================================================================
' EXCEL VBA - WEBAPP INTEGRATION GATEWAY DEMO MODULE
' ==============================================================================
' This module demonstrates how the Excel macro workbook (TaiHoaDonDienTu_v6.2.xlsm)
' can communicate directly with the local running Webapp (http://127.0.0.1:5000)
' for high-performance features:
' 1. Retrieve registered Taxpayers (MSTs).
' 2. Solve GDT SVG Captcha instantly using the offline vector engine.
' 3. Sync downloaded invoices & line items to the webapp for automated compliance auditing.
' ==============================================================================

Option Explicit

Private Const WEBAPP_BASE_URL As String = "http://127.0.0.1:5000"
Private Const VBA_SECRET_TOKEN As String = "vba-secret-token-123" ' Must match vba_gateway_token in SystemConfig

' ------------------------------------------------------------------------------
' 1. Solve GDT Captcha Offline
' ------------------------------------------------------------------------------
Public Function SolveCaptchaOffline(ByVal svgContent As String, Optional ByVal captchaKey As String = "") As String
    Dim http As Object
    Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    
    Dim url As String
    url = WEBAPP_BASE_URL & "/api/v1/vba/solve-captcha"
    
    ' Construct JSON payload
    Dim payload As String
    payload = "{""svg_content"": " & JsonEscape(svgContent) & _
              ", ""captcha_key"": """ & captchaKey & """}"
              
    On Error GoTo ErrorHandler
    
    http.Open "POST", url, False
    http.setRequestHeader "Content-Type", "application/json; charset=utf-8"
    http.setRequestHeader "X-VBA-Token", VBA_SECRET_TOKEN
    http.send payload
    
    If http.Status = 200 Then
        Dim responseText As String
        responseText = http.responseText
        
        ' Quick JSON parsing for "solution" field
        Dim solution As String
        solution = ExtractJsonField(responseText, "solution")
        
        SolveCaptchaOffline = solution
    Else
        MsgBox "Webapp Captcha Solver returned status: " & http.Status & vbCrLf & http.responseText, vbExclamation, "Error"
        SolveCaptchaOffline = ""
    End If
    Exit Function
    
ErrorHandler:
    MsgBox "Could not connect to Webapp Captcha Solver at " & WEBAPP_BASE_URL & vbCrLf & "Make sure the webapp is running locally.", vbCritical, "Connection Error"
    SolveCaptchaOffline = ""
End Function

' ------------------------------------------------------------------------------
' 2. Retrieve Taxpayers List
' ------------------------------------------------------------------------------
Public Sub FetchTaxpayersFromWebapp()
    Dim http As Object
    Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    
    Dim url As String
    url = WEBAPP_BASE_URL & "/api/v1/vba/taxpayers"
    
    On Error GoTo ErrorHandler
    
    http.Open "GET", url, False
    http.setRequestHeader "X-VBA-Token", VBA_SECRET_TOKEN
    http.send
    
    If http.Status = 200 Then
        MsgBox "Successfully fetched Taxpayers list:" & vbCrLf & vbCrLf & http.responseText, vbInformation, "Taxpayers Sync"
    Else
        MsgBox "Failed to fetch taxpayers: " & http.Status, vbExclamation, "Error"
    End If
    Exit Sub
    
ErrorHandler:
    MsgBox "Error fetching taxpayers: " & Err.Description, vbCritical, "Connection Error"
End Sub

' ------------------------------------------------------------------------------
' 3. Sync Invoices from Excel Sheet to Webapp for Real-Time Auditing
' ------------------------------------------------------------------------------
Public Sub SyncInvoicesToWebapp()
    Dim http As Object
    Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    
    Dim url As String
    url = WEBAPP_BASE_URL & "/api/v1/vba/sync-invoices"
    
    ' Build sample payload matching invoices/routes/vba_gateway.py schema
    ' In production, loop through your Excel rows to build this dynamically
    Dim jsonPayload As String
    jsonPayload = "{""taxpayer_mst"": ""0102030499"", ""invoices"": [" & _
        "{" & _
            """seller_mst"": ""0123456789""," & _
            """symbol"": ""1C26TAA""," & _
            """number"": ""0000123""," & _
            """date"": ""2026-06-25""," & _
            """seller_name"": ""Nha Cung Cap Thu A""," & _
            """buyer_name"": ""Cong ty Mua B""," & _
            """buyer_mst"": ""0102030499""," & _
            """amount_before_tax"": 1000000.0," & _
            """tax_amount"": 80000.0," & _
            """total_amount"": 1080000.0," & _
            """has_signature"": true," & _
            """signing_date"": ""2026-06-25""," & _
            """invoice_status"": ""Đã cấp mã""," & _
            """items"": [" & _
                "{" & _
                    """item_name"": ""Phần mềm kế toán doanh nghiệp""," & _
                    """quantity"": 1," & _
                    """unit_price"": 1000000," & _
                    """amount_before_tax"": 1000000," & _
                    """tax_rate"": ""8%""," & _
                    """tax_amount"": 80000," & _
                    """amount_after_tax"": 1080000" & _
                "}" & _
            "]" & _
        "}" & _
    "]}"

    On Error GoTo ErrorHandler
    
    http.Open "POST", url, False
    http.setRequestHeader "Content-Type", "application/json; charset=utf-8"
    http.setRequestHeader "X-VBA-Token", VBA_SECRET_TOKEN
    http.send jsonPayload
    
    If http.Status = 200 Then
        MsgBox "Synchronized successfully!" & vbCrLf & vbCrLf & http.responseText, vbInformation, "Sync Complete"
    Else
        MsgBox "Sync failed: " & http.Status & vbCrLf & http.responseText, vbExclamation, "Sync Error"
    End If
    Exit Sub
    
ErrorHandler:
    MsgBox "Error syncing invoices: " & Err.Description, vbCritical, "Connection Error"
End Sub

' ------------------------------------------------------------------------------
' Private Helpers
' ------------------------------------------------------------------------------
Private Function JsonEscape(ByVal txt As String) As String
    Dim val As String
    val = txt
    val = Replace(val, "\", "\\")
    val = Replace(val, """", "\""")
    val = Replace(val, vbCrLf, "\n")
    val = Replace(val, vbCr, "\n")
    val = Replace(val, vbLf, "\n")
    JsonEscape = """" & val & """"
End Function

Private Function ExtractJsonField(ByVal json As String, ByVal fieldName As String) As String
    Dim key As String
    key = """" & fieldName & """:"
    
    Dim pos As Long
    pos = InStr(json, key)
    If pos = 0 Then
        ExtractJsonField = ""
        Exit Function
    End If
    
    ' Find start of value after colon
    pos = pos + Len(key)
    Do While Mid(json, pos, 1) = " " Or Mid(json, pos, 1) = vbTab
        pos = pos + 1
    Loop
    
    Dim char As String
    char = Mid(json, pos, 1)
    
    If char = """" Then
        ' String value
        pos = pos + 1
        Dim endPos As Long
        endPos = InStr(pos, json, """")
        ExtractJsonField = Mid(json, pos, endPos - pos)
    Else
        ' Numeric or boolean value
        Dim i As Long
        i = pos
        Do While i <= Len(json)
            char = Mid(json, i, 1)
            If char = "," Or char = "}" Or char = "]" Or char = vbCr Or char = vbLf Then
                Exit Do
            End If
            i = i + 1
        Loop
        ExtractJsonField = Trim(Mid(json, pos, i - pos))
    End If
End Function
