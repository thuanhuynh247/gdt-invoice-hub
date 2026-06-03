import sys
from app import create_app

app = create_app()
with app.test_client() as client:
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['username'] = 'admin'
        sess['user_role'] = 'admin'
    
    response = client.get('/invoices')
    print("Status code:", response.status_code)
    print("Body length:", len(response.data))
    if response.status_code == 500:
        print("Response data:", response.data.decode('utf-8'))
