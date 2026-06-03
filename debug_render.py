import sys
from flask import session
from app import create_app

app = create_app()
with app.test_request_context('/invoices'):
    # Simulate the exact session variables set during login
    session['logged_in'] = True
    session['username'] = 'admin'
    session['display_name'] = 'admin'
    session['user_role'] = 'admin'
    session['tax_code'] = None  # Mock mode admin has MST None initially
    
    # Process request using Flask's preprocess_request, which runs before_request
    app.preprocess_request()
    
    try:
        from flask import render_template
        rendered = render_template("invoices.html",
                                   logged_in=session.get("logged_in"),
                                   session_username=session.get("display_name") or session.get("username"))
        print("Render succeeded! Length:", len(rendered))
    except Exception as e:
        import traceback
        print("Render failed!")
        traceback.print_exc()
