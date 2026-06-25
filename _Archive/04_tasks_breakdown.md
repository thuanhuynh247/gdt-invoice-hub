\# Tasks: Invoice Download Webapp - Implementation Breakdown

\*\*Project Code\*\*: INVOICE-WEBAPP-PLAN-A  

\*\*Version\*\*: 1.0  

\*\*Date\*\*: 2026-05-19  

\*\*Status\*\*: ✅ READY FOR IMPLEMENTATION



\---



\## 📝 How to Use This Task List



\- \*\*Sequence\*\*: Follow order top-to-bottom (dependencies respected)

\- \*\*\[P]\*\*: Tasks marked with \[P] can run in PARALLEL with previous tasks

\- \*\*\[T]\*\*: Test-driven: write tests BEFORE implementation

\- \*\*Checkpoints\*\*: After each section, verify working before moving on

\- \*\*Blockers\*\*: Mark as 🔴 BLOCKED if stuck, don't skip



\---



\## PHASE 1: PROJECT SETUP \& LEARNING



\### Task 1.1 - Environment Setup \& Virtual Environment

\*\*Dependency\*\*: None  

\*\*Duration\*\*: 30 minutes  

\*\*Description\*\*: Create project folder, Python venv, install dependencies



\*\*Steps\*\*:

1\. Create folder: `mkdir invoice-webapp \&\& cd invoice-webapp`

2\. Create venv: `python -m venv venv`

3\. Activate venv: `source venv/bin/activate` (Mac/Linux) or `venv\\Scripts\\activate` (Windows)

4\. Create `requirements.txt`:

&#x20;  ```

&#x20;  Flask==2.3.3

&#x20;  requests==2.31.0

&#x20;  selenium==4.13.0

&#x20;  openpyxl==3.1.2

&#x20;  python-dotenv==1.0.0

&#x20;  pytest==7.4.2

&#x20;  pytest-cov==4.1.0

&#x20;  ```

5\. Install: `pip install -r requirements.txt`

6\. Verify: `python -c "import flask; print(flask.\_\_version\_\_)"`

7\. Create `.env.example`:

&#x20;  ```

&#x20;  GDT\_USERNAME=your\_username

&#x20;  GDT\_PASSWORD=your\_password

&#x20;  FLASK\_SECRET\_KEY=your\_secret\_key

&#x20;  DEBUG=True

&#x20;  ```

8\. Create `.gitignore`:

&#x20;  ```

&#x20;  venv/

&#x20;  .env

&#x20;  \_\_pycache\_\_/

&#x20;  \*.pyc

&#x20;  .pytest\_cache/

&#x20;  ```



\*\*Output\*\*: Folder structure + venv ready, all packages installed  

\*\*Verification\*\*: Can run Python and import Flask  

\*\*Status\*\*: ⬜ Not Started | 📝 In Progress | ✅ Complete



\---



\### Task 1.2 - Create Flask App Skeleton

\*\*Dependency\*\*: Task 1.1  

\*\*Duration\*\*: 45 minutes  

\*\*Description\*\*: Create basic Flask app structure with logging



\*\*Create `app.py`\*\*:

```python

from flask import Flask, render\_template, jsonify, session, redirect

from dotenv import load\_dotenv

import os

from datetime import timedelta



load\_dotenv()



app = Flask(\_\_name\_\_)



\# Configuration

app.config\['SECRET\_KEY'] = os.getenv('FLASK\_SECRET\_KEY', 'dev-secret-key-change-in-prod')

app.config\['SESSION\_COOKIE\_HTTPONLY'] = True

app.config\['PERMANENT\_SESSION\_LIFETIME'] = timedelta(minutes=30)

app.config\['SESSION\_REFRESH\_EACH\_REQUEST'] = True



\# Create folders if not exist

os.makedirs('logs', exist\_ok=True)



\# Error handlers

@app.errorhandler(404)

def not\_found(error):

&#x20;   return jsonify({'error': 'Page not found'}), 404



@app.errorhandler(500)

def server\_error(error):

&#x20;   return jsonify({'error': 'Server error'}), 500



\# Simple test route

@app.route('/')

def index():

&#x20;   return render\_template('base.html')



if \_\_name\_\_ == '\_\_main\_\_':

&#x20;   app.run(debug=os.getenv('DEBUG', True), host='localhost', port=5000)

```



\*\*Create folder structure\*\*:

```bash

mkdir -p templates static/css static/js static/images tests auth invoices export docs

```



\*\*Create `templates/base.html`\*\*:

```html

<!DOCTYPE html>

<html lang="vi">

<head>

&#x20;   <meta charset="UTF-8">

&#x20;   <meta name="viewport" content="width=device-width, initial-scale=1.0">

&#x20;   <title>Invoice Download Webapp</title>

&#x20;   <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">

&#x20;   <link rel="stylesheet" href="{{ url\_for('static', filename='css/style.css') }}">

</head>

<body>

&#x20;   <nav class="navbar navbar-expand-lg navbar-dark bg-dark">

&#x20;       <div class="container-fluid">

&#x20;           <a class="navbar-brand" href="/">📄 Invoice Webapp</a>

&#x20;       </div>

&#x20;   </nav>

&#x20;   

&#x20;   <main class="container mt-5">

&#x20;       {% block content %}{% endblock %}

&#x20;   </main>



&#x20;   <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>

&#x20;   <script src="{{ url\_for('static', filename='js/main.js') }}"></script>

</body>

</html>

```



\*\*Create `static/css/style.css`\*\*:

```css

:root {

&#x20;   --primary-color: #007bff;

&#x20;   --danger-color: #dc3545;

&#x20;   --success-color: #28a745;

&#x20;   --text-color: #333;

}



body {

&#x20;   font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;

&#x20;   background-color: #f5f5f5;

}



.navbar {

&#x20;   box-shadow: 0 2px 4px rgba(0,0,0,0.1);

}



.form-control, .btn {

&#x20;   font-size: 14px;

}



.btn {

&#x20;   border-radius: 4px;

&#x20;   padding: 8px 16px;

}



.spinner-border {

&#x20;   display: none;

}



.spinner-border.show {

&#x20;   display: inline-block;

}

```



\*\*Create `static/js/main.js`\*\*:

```javascript

// Utility: Show loading spinner

function showLoader(show = true) {

&#x20;   const spinner = document.querySelector('.spinner-border');

&#x20;   if (spinner) {

&#x20;       if (show) {

&#x20;           spinner.classList.add('show');

&#x20;       } else {

&#x20;           spinner.classList.remove('show');

&#x20;       }

&#x20;   }

}



// Utility: Show toast message

function showToast(message, type = 'info') {

&#x20;   const alertClass = {

&#x20;       'success': 'alert-success',

&#x20;       'error': 'alert-danger',

&#x20;       'info': 'alert-info',

&#x20;       'warning': 'alert-warning'

&#x20;   }\[type] || 'alert-info';

&#x20;   

&#x20;   const alert = document.createElement('div');

&#x20;   alert.className = `alert ${alertClass} alert-dismissible fade show`;

&#x20;   alert.setAttribute('role', 'alert');

&#x20;   alert.innerHTML = `

&#x20;       ${message}

&#x20;       <button type="button" class="btn-close" data-bs-dismiss="alert"></button>

&#x20;   `;

&#x20;   

&#x20;   document.body.insertBefore(alert, document.body.firstChild);

&#x20;   

&#x20;   // Auto-dismiss after 5 seconds

&#x20;   setTimeout(() => alert.remove(), 5000);

}



// Utility: Make API call with error handling

async function apiCall(url, options = {}) {

&#x20;   try {

&#x20;       showLoader(true);

&#x20;       const response = await fetch(url, {

&#x20;           ...options,

&#x20;           headers: {

&#x20;               'Content-Type': 'application/json',

&#x20;               ...options.headers

&#x20;           }

&#x20;       });

&#x20;       

&#x20;       if (response.status === 401) {

&#x20;           // Unauthorized - redirect to login

&#x20;           window.location.href = '/login';

&#x20;           return null;

&#x20;       }

&#x20;       

&#x20;       if (!response.ok) {

&#x20;           throw new Error(`HTTP ${response.status}: ${response.statusText}`);

&#x20;       }

&#x20;       

&#x20;       return await response.json();

&#x20;   } catch (error) {

&#x20;       showToast(`Lỗi: ${error.message}`, 'error');

&#x20;       console.error('API Error:', error);

&#x20;       return null;

&#x20;   } finally {

&#x20;       showLoader(false);

&#x20;   }

}



console.log('Invoice Webapp JS loaded');

```



\*\*Output\*\*: Flask app runs, can access http://localhost:5000  

\*\*Verification\*\*: `python app.py` starts server, no import errors  

\*\*Status\*\*: ⬜ Not Started | 📝 In Progress | ✅ Complete



\---



\### ✅ CHECKPOINT 1: Can run `python app.py` and access http://localhost:5000



\---



\## PHASE 2: PYTHON \& FLASK LEARNING



\### Task 2.1 - Learn Python Basics (30 min read/practice)

\*\*Dependency\*\*: Task 1.1  

\*\*Duration\*\*: 2-3 hours  

\*\*Description\*\*: Understand Python fundamentals



\*\*Topics to cover\*\*:

1\. Variables and data types: `name = "John"`, `age = 30`

2\. Functions: `def greet(name): return f"Hello {name}"`

3\. Loops: `for`, `while`

4\. Dictionaries: `{"key": "value"}`

5\. List comprehensions: `\[x\*2 for x in range(5)]`



\*\*Practice\*\*: Write 5 small scripts testing these concepts  

\*\*Verification\*\*: Can write and run basic Python script without error  

\*\*Status\*\*: ⬜ Not Started | 📝 In Progress | ✅ Complete



\---



\### Task 2.2 - Learn Flask Routing \& Request Handling

\*\*Dependency\*\*: Task 2.1  

\*\*Duration\*\*: 2-3 hours  

\*\*Description\*\*: Understand Flask @app.route and request/response



\*\*Concepts\*\*:

1\. Routes: `@app.route('/path')` maps URL to function

2\. Methods: GET (fetch) vs POST (submit)

3\. Request object: `request.form\['key']`, `request.args.get('key')`

4\. Response: Return dict (auto JSON), HTML, or file

5\. Status codes: 200 (OK), 400 (bad request), 401 (unauthorized), 500 (error)



\*\*Practice\*\*:

\- Create 3 GET routes in `app.py`

\- Create 1 POST route that accepts JSON, returns JSON

\- Test with curl or Postman



\*\*Verification\*\*: Routes work as expected  

\*\*Status\*\*: ⬜ Not Started | 📝 In Progress | ✅ Complete



\---



\### Task 2.3 - Learn Flask Sessions \& Cookies

\*\*Dependency\*\*: Task 2.2  

\*\*Duration\*\*: 1-2 hours  

\*\*Description\*\*: Understand session storage (keeping user logged in)



\*\*Concepts\*\*:

1\. `flask.session` dictionary (encrypted browser cookie)

2\. `session\['user\_id'] = value` to store

3\. `session.get('user\_id')` to retrieve

4\. Session timeout \& cleanup

5\. CSRF protection (why important)



\*\*Practice\*\*:

\- Create /set-session route that stores data

\- Create /get-session route that retrieves data

\- Verify session persists on page refresh

\- Verify session clears on browser close



\*\*Verification\*\*: Session management works  

\*\*Status\*\*: ⬜ Not Started | 📝 In Progress | ✅ Complete



\---



\### ✅ CHECKPOINT 2: Understand Python basics, Flask routing, and sessions



\---



\## PHASE 3: API ANALYSIS \& RESEARCH



\### Task 3.1 - Analyze gdt.gov.vn Login Flow

\*\*Dependency\*\*: None (can do in parallel)  

\*\*Duration\*\*: 2-3 hours  

\*\*Description\*\*: Reverse-engineer gdt.gov.vn authentication



\*\*Steps\*\*:

1\. Open https://hoadondientu.gdt.gov.vn/ on Chrome

2\. Open DevTools (F12 → Network tab)

3\. Clear network log (Ctrl+Shift+K)

4\. Type username and password (don't submit yet)

5\. Document form fields: username, password, any hidden fields

6\. Solve Captcha (or screenshot it)

7\. Click login button

8\. Capture the POST request:

&#x20;  - URL: `POST to where?`

&#x20;  - Body: `{what fields?}`

&#x20;  - Response: `{what data?}`

&#x20;  - Cookies: `What gets set?`



\*\*Document in `docs/API\_ANALYSIS.md`\*\*:

```markdown

\# gdt.gov.vn API Analysis



\## Login Endpoint

\- URL: POST https://hoadondientu.gdt.gov.vn/... \[FILL IN]

\- Headers: Content-Type: application/x-www-form-urlencoded (or JSON?)

\- Body: 

&#x20; - username: string

&#x20; - password: string

&#x20; - captcha\_answer: string (or other name?)

\- Response: 

&#x20; - Success (200): {token? session? cookies?}

&#x20; - Failure (401): {error message?}

\- Cookies set: \[what names?]

\- Session lifetime: \[how long?]



\## Captcha

\- Image URL: https://... \[FILL IN]

\- Verification method: \[auto solve or manual entry?]

\- Answer format: \[numbers? letters?]

```



\*\*Output\*\*: Documented login endpoint  

\*\*Status\*\*: ⬜ Not Started | 📝 In Progress | ✅ Complete



\---



\### Task 3.2 - Analyze gdt.gov.vn Invoice Fetch

\*\*Dependency\*\*: Task 3.1  

\*\*Duration\*\*: 1-2 hours  

\*\*Description\*\*: Find invoice list API endpoint



\*\*Steps\*\*:

1\. Login to gdt.gov.vn in browser

2\. Open DevTools Network tab

3\. Navigate to invoice list page

4\. Capture the request that fetches invoices:

&#x20;  - URL: `GET/POST to where?`

&#x20;  - Query params: `?date\_from=...\&date\_to=...?`

&#x20;  - Response format: `JSON? XML?`

&#x20;  - Response fields: `\[what's in each invoice?]`



\*\*Document in API\_ANALYSIS.md\*\*:

```markdown

\## Invoice List Endpoint

\- URL: GET https://... \[FILL IN]

\- Query params:

&#x20; - from: YYYY-MM-DD format (example: 2026-05-01)

&#x20; - to: YYYY-MM-DD format (example: 2026-05-31)

\- Authentication: \[Session cookie? Bearer token?]

\- Response format: JSON or XML?

\- Response fields:

&#x20; - id: string

&#x20; - date: timestamp or string?

&#x20; - amount: number or string?

&#x20; - status: enum values?

&#x20; - issuer: string?

&#x20; - \[other fields?]

\- Example response: \[paste sample]

```



\*\*Output\*\*: Documented invoice fetch endpoint  

\*\*Status\*\*: ⬜ Not Started | 📝 In Progress | ✅ Complete



\---



\### Task 3.3 - Analyze Invoice Download Endpoint

\*\*Dependency\*\*: Task 3.1  

\*\*Duration\*\*: 1 hour  

\*\*Description\*\*: Find individual invoice download



\*\*Steps\*\*:

1\. In invoice list, click "Download" for one invoice

2\. Capture request:

&#x20;  - URL: `GET/POST to where?`

&#x20;  - Params: `{invoice\_id}?`

&#x20;  - Response: `Binary XML file?`



\*\*Document in API\_ANALYSIS.md\*\*:

```markdown

\## Invoice Download Endpoint

\- URL: GET https://... \[FILL IN]

\- Params: invoice\_id = ???

\- Response: Binary XML file

\- Content-Type: application/xml or text/xml

```



\*\*Output\*\*: Documented download endpoint  

\*\*Status\*\*: ⬜ Not Started | 📝 In Progress | ✅ Complete



\---



\### ✅ CHECKPOINT 3: API\_ANALYSIS.md complete with 3+ endpoints documented



\---



\## PHASE 4: BACKEND IMPLEMENTATION



\### Task 4.1 - \[T] Write Auth Login Tests

\*\*Dependency\*\*: Task 3.1  

\*\*Duration\*\*: 1 hour  

\*\*Description\*\*: Write tests BEFORE implementing



\*\*Create `tests/test\_auth.py`\*\*:

```python

import pytest

from app import app



@pytest.fixture

def client():

&#x20;   app.config\['TESTING'] = True

&#x20;   with app.test\_client() as client:

&#x20;       yield client



def test\_login\_page\_loads(client):

&#x20;   """Test that login page loads"""

&#x20;   response = client.get('/login')

&#x20;   assert response.status\_code == 200

&#x20;   assert b'username' in response.data  # Form has username field



def test\_login\_post\_valid\_credentials(client):

&#x20;   """Test POST /api/auth/login with valid credentials"""

&#x20;   response = client.post('/api/auth/login', 

&#x20;       json={'username': 'test\_user', 'password': 'test\_pass', 'captcha': '1234'})

&#x20;   assert response.status\_code == 200

&#x20;   data = response.get\_json()

&#x20;   assert data\['status'] == 'success'



def test\_login\_post\_invalid\_credentials(client):

&#x20;   """Test POST /api/auth/login with invalid credentials"""

&#x20;   response = client.post('/api/auth/login',

&#x20;       json={'username': 'wrong', 'password': 'wrong', 'captcha': '1234'})

&#x20;   assert response.status\_code == 401

&#x20;   data = response.get\_json()

&#x20;   assert 'error' in data



def test\_session\_set\_after\_login(client):

&#x20;   """Test that session is set after successful login"""

&#x20;   # Mock the gdt.gov.vn API call

&#x20;   response = client.post('/api/auth/login',

&#x20;       json={'username': 'test', 'password': 'test', 'captcha': '1234'})

&#x20;   # Verify session cookie was set (would need mocking)

```



\*\*Output\*\*: Test file created, tests ready to run  

\*\*Status\*\*: ⬜ Not Started | 📝 In Progress | ✅ Complete



\---



\### Task 4.2 - Implement Auth Login Route

\*\*Dependency\*\*: Task 4.1  

\*\*Duration\*\*: 2-3 hours  

\*\*Description\*\*: Implement actual login logic



\*\*Create `auth/login.py`\*\*:

```python

from flask import request, jsonify, session

from datetime import datetime, timedelta

import requests

import os



def handle\_login():

&#x20;   """Handle user login"""

&#x20;   data = request.get\_json()

&#x20;   username = data.get('username', '').strip()

&#x20;   password = data.get('password', '').strip()

&#x20;   captcha = data.get('captcha', '').strip()

&#x20;   

&#x20;   # Validate inputs

&#x20;   if not username or not password or not captcha:

&#x20;       return jsonify({'error': 'Thông tin không đủ'}), 400

&#x20;   

&#x20;   # Call gdt.gov.vn login API

&#x20;   # TODO: Replace with actual endpoint from API\_ANALYSIS.md

&#x20;   gdt\_url = "https://hoadondientu.gdt.gov.vn/login"

&#x20;   try:

&#x20;       response = requests.post(gdt\_url, 

&#x20;           data={'username': username, 'password': password, 'captcha': captcha},

&#x20;           timeout=10)

&#x20;       

&#x20;       if response.status\_code != 200:

&#x20;           return jsonify({'error': 'Thông tin đăng nhập không đúng'}), 401

&#x20;       

&#x20;       # Store session

&#x20;       session\['username'] = username

&#x20;       session\['login\_time'] = datetime.now().isoformat()

&#x20;       session\['expires\_at'] = (datetime.now() + timedelta(minutes=30)).isoformat()

&#x20;       session.permanent = True

&#x20;       

&#x20;       return jsonify({

&#x20;           'status': 'success',

&#x20;           'message': 'Đăng nhập thành công',

&#x20;           'expires\_at': session\['expires\_at']

&#x20;       }), 200

&#x20;   

&#x20;   except requests.RequestException as e:

&#x20;       return jsonify({'error': f'Lỗi kết nối: {str(e)}'}), 503



def handle\_logout():

&#x20;   """Handle user logout"""

&#x20;   session.clear()

&#x20;   return jsonify({'status': 'logged out'}), 200



def get\_session\_status():

&#x20;   """Get current session status"""

&#x20;   if 'username' not in session:

&#x20;       return jsonify({'logged\_in': False}), 200

&#x20;   

&#x20;   expires\_at = datetime.fromisoformat(session\['expires\_at'])

&#x20;   expires\_in = (expires\_at - datetime.now()).total\_seconds()

&#x20;   

&#x20;   return jsonify({

&#x20;       'logged\_in': True,

&#x20;       'username': session\['username'],

&#x20;       'expires\_in': int(expires\_in)

&#x20;   }), 200

```



\*\*Update `app.py` to include routes\*\*:

```python

from auth.login import handle\_login, handle\_logout, get\_session\_status



@app.route('/login', methods=\['GET'])

def login\_page():

&#x20;   return render\_template('login.html')



@app.route('/api/auth/login', methods=\['POST'])

def api\_login():

&#x20;   return handle\_login()



@app.route('/api/auth/logout', methods=\['POST'])

def api\_logout():

&#x20;   return handle\_logout()



@app.route('/api/session-status', methods=\['GET'])

def api\_session\_status():

&#x20;   return get\_session\_status()

```



\*\*Create `templates/login.html`\*\*:

```html

{% extends "base.html" %}



{% block content %}

<div class="row justify-content-center">

&#x20;   <div class="col-md-6">

&#x20;       <div class="card">

&#x20;           <div class="card-body">

&#x20;               <h3 class="card-title mb-4">Đăng nhập</h3>

&#x20;               <form id="loginForm">

&#x20;                   <div class="mb-3">

&#x20;                       <label for="username" class="form-label">Tên đăng nhập</label>

&#x20;                       <input type="text" class="form-control" id="username" name="username" required>

&#x20;                   </div>

&#x20;                   <div class="mb-3">

&#x20;                       <label for="password" class="form-label">Mật khẩu</label>

&#x20;                       <input type="password" class="form-control" id="password" name="password" required>

&#x20;                   </div>

&#x20;                   <div class="mb-3">

&#x20;                       <label for="captcha" class="form-label">Captcha</label>

&#x20;                       <input type="text" class="form-control" id="captcha" name="captcha" placeholder="Nhập mã Captcha" required>

&#x20;                   </div>

&#x20;                   <button type="submit" class="btn btn-primary w-100">Đăng nhập</button>

&#x20;                   <div class="spinner-border mt-3" role="status">

&#x20;                       <span class="visually-hidden">Loading...</span>

&#x20;                   </div>

&#x20;               </form>

&#x20;           </div>

&#x20;       </div>

&#x20;   </div>

</div>



<script>

document.getElementById('loginForm').addEventListener('submit', async (e) => {

&#x20;   e.preventDefault();

&#x20;   

&#x20;   const username = document.getElementById('username').value;

&#x20;   const password = document.getElementById('password').value;

&#x20;   const captcha = document.getElementById('captcha').value;

&#x20;   

&#x20;   const data = await apiCall('/api/auth/login', {

&#x20;       method: 'POST',

&#x20;       body: JSON.stringify({username, password, captcha\_answer: captcha})

&#x20;   });

&#x20;   

&#x20;   if (data \&\& data.status === 'success') {

&#x20;       showToast('Đăng nhập thành công', 'success');

&#x20;       window.location.href = '/invoices';

&#x20;   }

});

</script>

{% endblock %}

```



\*\*Run tests\*\*: `pytest tests/test\_auth.py -v`  

\*\*Output\*\*: Login route works, tests passing  

\*\*Status\*\*: ⬜ Not Started | 📝 In Progress | ✅ Complete



\---



\### Task 4.3 - \[T] Write Invoice Fetch Tests

\*\*Dependency\*\*: Task 3.2  

\*\*Duration\*\*: 1 hour  

\*\*Description\*\*: Write tests for invoice API



\*\*Create `tests/test\_invoices.py`\*\*:

```python

def test\_fetch\_invoices\_valid\_date\_range(client):

&#x20;   """Test GET /api/invoices with valid date range"""

&#x20;   # Would need to be logged in

&#x20;   response = client.get('/api/invoices?from=2026-05-01\&to=2026-05-31')

&#x20;   assert response.status\_code == 200

&#x20;   data = response.get\_json()

&#x20;   assert 'invoices' in data

&#x20;   assert 'total\_count' in data

&#x20;   assert isinstance(data\['invoices'], list)



def test\_fetch\_invoices\_invalid\_date\_format(client):

&#x20;   """Test with invalid date format"""

&#x20;   response = client.get('/api/invoices?from=05-01-2026\&to=05-31-2026')

&#x20;   assert response.status\_code == 400



def test\_fetch\_invoices\_empty\_result(client):

&#x20;   """Test when no invoices found"""

&#x20;   response = client.get('/api/invoices?from=2020-01-01\&to=2020-01-02')

&#x20;   assert response.status\_code == 200

&#x20;   data = response.get\_json()

&#x20;   assert data\['total\_count'] == 0

```



\*\*Output\*\*: Test file created  

\*\*Status\*\*: ⬜ Not Started | 📝 In Progress | ✅ Complete



\---



\### Task 4.4 - Implement Invoice Fetch Route

\*\*Dependency\*\*: Task 4.3  

\*\*Duration\*\*: 3-4 hours  

\*\*Description\*\*: Implement invoice search



\*\*Create `invoices/service.py`\*\*:

```python

import requests

from flask import session



def fetch\_invoices\_from\_gdt(date\_from, date\_to):

&#x20;   """Fetch invoices from gdt.gov.vn API"""

&#x20;   # TODO: Replace URL from API\_ANALYSIS.md

&#x20;   gdt\_url = "https://hoadondientu.gdt.gov.vn/api/invoices"

&#x20;   

&#x20;   # Get session cookie (would need to extract from login)

&#x20;   headers = {

&#x20;       'Content-Type': 'application/json'

&#x20;   }

&#x20;   

&#x20;   params = {

&#x20;       'from': date\_from,

&#x20;       'to': date\_to

&#x20;   }

&#x20;   

&#x20;   try:

&#x20;       response = requests.get(gdt\_url, params=params, headers=headers, timeout=30)

&#x20;       response.raise\_for\_status()

&#x20;       

&#x20;       # Parse response (JSON or XML depending on API)

&#x20;       data = response.json()  # or parse XML

&#x20;       return data

&#x20;   

&#x20;   except requests.RequestException as e:

&#x20;       raise Exception(f"Lỗi gọi API: {str(e)}")

```



\*\*Create `invoices/parser.py`\*\*:

```python

from datetime import datetime



def parse\_invoice\_list(api\_response):

&#x20;   """Parse gdt.gov.vn response into normalized format"""

&#x20;   invoices = \[]

&#x20;   

&#x20;   # TODO: Adjust based on actual API response format

&#x20;   for invoice\_data in api\_response.get('invoices', \[]):

&#x20;       invoice = {

&#x20;           'id': invoice\_data.get('invoice\_id'),

&#x20;           'date': invoice\_data.get('invoice\_date'),

&#x20;           'amount': invoice\_data.get('total\_amount'),

&#x20;           'status': invoice\_data.get('status'),

&#x20;           'issuer': invoice\_data.get('issuer\_name')

&#x20;       }

&#x20;       invoices.append(invoice)

&#x20;   

&#x20;   return invoices



def validate\_date\_format(date\_str):

&#x20;   """Validate date is in YYYY-MM-DD format"""

&#x20;   try:

&#x20;       datetime.strptime(date\_str, '%Y-%m-%d')

&#x20;       return True

&#x20;   except ValueError:

&#x20;       return False

```



\*\*Update `app.py`\*\*:

```python

from invoices.service import fetch\_invoices\_from\_gdt

from invoices.parser import parse\_invoice\_list, validate\_date\_format



@app.route('/invoices', methods=\['GET'])

def invoices\_page():

&#x20;   if 'username' not in session:

&#x20;       return redirect('/login')

&#x20;   return render\_template('invoices.html')



@app.route('/api/invoices', methods=\['GET'])

def api\_invoices():

&#x20;   if 'username' not in session:

&#x20;       return jsonify({'error': 'Chưa đăng nhập'}), 401

&#x20;   

&#x20;   date\_from = request.args.get('from')

&#x20;   date\_to = request.args.get('to')

&#x20;   

&#x20;   # Validate dates

&#x20;   if not validate\_date\_format(date\_from) or not validate\_date\_format(date\_to):

&#x20;       return jsonify({'error': 'Format ngày không đúng (YYYY-MM-DD)'}), 400

&#x20;   

&#x20;   if date\_from > date\_to:

&#x20;       return jsonify({'error': 'Từ ngày phải nhỏ hơn đến ngày'}), 400

&#x20;   

&#x20;   try:

&#x20;       response = fetch\_invoices\_from\_gdt(date\_from, date\_to)

&#x20;       invoices = parse\_invoice\_list(response)

&#x20;       return jsonify({

&#x20;           'total\_count': len(invoices),

&#x20;           'invoices': invoices

&#x20;       }), 200

&#x20;   except Exception as e:

&#x20;       return jsonify({'error': str(e)}), 503

```



\*\*Output\*\*: Invoice fetch route working  

\*\*Status\*\*: ⬜ Not Started | 📝 In Progress | ✅ Complete



\---



\### Task 4.5 - \[P] \[T] Write Excel Export Tests

\*\*Dependency\*\*: None (parallel with 4.4)  

\*\*Duration\*\*: 1 hour  

\*\*Description\*\*: Write tests for Excel generation



\*\*Create `tests/test\_excel.py`\*\*:

```python

from export.excel import generate\_excel



def test\_generate\_excel\_valid\_data():

&#x20;   """Test Excel generation with valid data"""

&#x20;   invoices = \[

&#x20;       {'id': 'INV001', 'date': '2026-05-01', 'amount': 1000000, 'status': 'paid', 'issuer': 'Company A'},

&#x20;       {'id': 'INV002', 'date': '2026-05-02', 'amount': 2000000, 'status': 'pending', 'issuer': 'Company B'},

&#x20;   ]

&#x20;   excel\_bytes = generate\_excel(invoices)

&#x20;   assert excel\_bytes is not None

&#x20;   assert len(excel\_bytes) > 0



def test\_generate\_excel\_empty\_data():

&#x20;   """Test Excel generation with no data"""

&#x20;   excel\_bytes = generate\_excel(\[])

&#x20;   assert excel\_bytes is not None

&#x20;   assert len(excel\_bytes) > 0  # Should still have headers

```



\*\*Output\*\*: Test file created  

\*\*Status\*\*: ⬜ Not Started | 📝 In Progress | ✅ Complete



\---



\### Task 4.6 - \[P] Implement Excel Export

\*\*Dependency\*\*: Task 4.5  

\*\*Duration\*\*: 2-3 hours  

\*\*Description\*\*: Implement Excel file generation



\*\*Create `export/excel.py`\*\*:

```python

from openpyxl import Workbook

from openpyxl.styles import Font, PatternFill, Alignment

from io import BytesIO



def generate\_excel(invoices):

&#x20;   """Generate Excel file from invoices"""

&#x20;   wb = Workbook()

&#x20;   ws = wb.active

&#x20;   ws.title = "Invoices"

&#x20;   

&#x20;   # Add headers

&#x20;   headers = \['Mã HĐ', 'Ngày', 'Số tiền', 'Trạng thái', 'Đơn vị phát hành']

&#x20;   ws.append(headers)

&#x20;   

&#x20;   # Format headers

&#x20;   header\_fill = PatternFill(start\_color='0070C0', end\_color='0070C0', fill\_type='solid')

&#x20;   header\_font = Font(bold=True, color='FFFFFF')

&#x20;   

&#x20;   for cell in ws\[1]:

&#x20;       cell.fill = header\_fill

&#x20;       cell.font = header\_font

&#x20;       cell.alignment = Alignment(horizontal='center', vertical='center')

&#x20;   

&#x20;   # Add data rows

&#x20;   for invoice in invoices:

&#x20;       ws.append(\[

&#x20;           invoice\['id'],

&#x20;           invoice\['date'],

&#x20;           invoice\['amount'],

&#x20;           invoice\['status'],

&#x20;           invoice\['issuer']

&#x20;       ])

&#x20;   

&#x20;   # Format columns

&#x20;   ws.column\_dimensions\['A'].width = 15

&#x20;   ws.column\_dimensions\['B'].width = 12

&#x20;   ws.column\_dimensions\['C'].width = 15

&#x20;   ws.column\_dimensions\['D'].width = 15

&#x20;   ws.column\_dimensions\['E'].width = 20

&#x20;   

&#x20;   # Save to bytes

&#x20;   output = BytesIO()

&#x20;   wb.save(output)

&#x20;   output.seek(0)

&#x20;   return output.getvalue()

```



\*\*Update `app.py`\*\*:

```python

from export.excel import generate\_excel



@app.route('/api/export-excel', methods=\['GET'])

def api\_export\_excel():

&#x20;   if 'username' not in session:

&#x20;       return jsonify({'error': 'Chưa đăng nhập'}), 401

&#x20;   

&#x20;   date\_from = request.args.get('from')

&#x20;   date\_to = request.args.get('to')

&#x20;   

&#x20;   # Validate dates (same as /api/invoices)

&#x20;   if not validate\_date\_format(date\_from) or not validate\_date\_format(date\_to):

&#x20;       return jsonify({'error': 'Format ngày không đúng'}), 400

&#x20;   

&#x20;   try:

&#x20;       response = fetch\_invoices\_from\_gdt(date\_from, date\_to)

&#x20;       invoices = parse\_invoice\_list(response)

&#x20;       excel\_bytes = generate\_excel(invoices)

&#x20;       

&#x20;       return send\_file(

&#x20;           BytesIO(excel\_bytes),

&#x20;           mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',

&#x20;           as\_attachment=True,

&#x20;           download\_name=f'invoices\_{date\_from}\_{date\_to}.xlsx'

&#x20;       )

&#x20;   except Exception as e:

&#x20;       return jsonify({'error': str(e)}), 503

```



\*\*Add to imports\*\*:

```python

from flask import send\_file

from io import BytesIO

```



\*\*Output\*\*: Excel export route working  

\*\*Status\*\*: ⬜ Not Started | 📝 In Progress | ✅ Complete



\---



\### ✅ CHECKPOINT 4: All backend routes working (/login, /api/invoices, /api/export-excel)



\---



\## PHASE 5: FRONTEND IMPLEMENTATION



\### Task 5.1 - Create Login Form

\*\*Dependency\*\*: Task 4.2  

\*\*Duration\*\*: 1 hour  

\*\*Description\*\*: Build interactive login page



\*\*Already created in Task 4.2\*\* - just enhance:

\- Add better error handling

\- Add loading state

\- Style with Bootstrap



\*\*Status\*\*: ✅ Complete from Task 4.2



\---



\### Task 5.2 - Create Invoice Search Page

\*\*Dependency\*\*: Task 4.4  

\*\*Duration\*\*: 2 hours  

\*\*Description\*\*: Build invoice list with search



\*\*Create `templates/invoices.html`\*\*:

```html

{% extends "base.html" %}



{% block content %}

<div class="container">

&#x20;   <h2>Tìm kiếm hóa đơn</h2>

&#x20;   

&#x20;   <div class="card mb-4">

&#x20;       <div class="card-body">

&#x20;           <form id="searchForm" class="row g-3">

&#x20;               <div class="col-md-4">

&#x20;                   <label for="dateFrom" class="form-label">Từ ngày</label>

&#x20;                   <input type="date" class="form-control" id="dateFrom" required>

&#x20;               </div>

&#x20;               <div class="col-md-4">

&#x20;                   <label for="dateTo" class="form-label">Đến ngày</label>

&#x20;                   <input type="date" class="form-control" id="dateTo" required>

&#x20;               </div>

&#x20;               <div class="col-md-4 d-flex align-items-end">

&#x20;                   <button type="submit" class="btn btn-primary w-100">Tìm kiếm</button>

&#x20;                   <button type="button" class="btn btn-success ms-2" id="exportBtn" style="display:none;">

&#x20;                       📥 Xuất Excel

&#x20;                   </button>

&#x20;               </div>

&#x20;           </form>

&#x20;       </div>

&#x20;   </div>

&#x20;   

&#x20;   <div id="resultsDiv" style="display:none;">

&#x20;       <h4>Kết quả (<span id="totalCount">0</span> hóa đơn)</h4>

&#x20;       <table class="table table-hover">

&#x20;           <thead>

&#x20;               <tr>

&#x20;                   <th>Mã HĐ</th>

&#x20;                   <th>Ngày</th>

&#x20;                   <th>Số tiền</th>

&#x20;                   <th>Trạng thái</th>

&#x20;                   <th>Đơn vị</th>

&#x20;                   <th>Hành động</th>

&#x20;               </tr>

&#x20;           </thead>

&#x20;           <tbody id="invoicesTable">

&#x20;           </tbody>

&#x20;       </table>

&#x20;   </div>

&#x20;   

&#x20;   <div id="emptyDiv" style="display:none;" class="alert alert-info">

&#x20;       Không có hóa đơn trong khoảng thời gian này

&#x20;   </div>

&#x20;   

&#x20;   <button type="button" class="btn btn-danger mt-3" id="logoutBtn">Đăng xuất</button>

</div>



<script>

document.getElementById('searchForm').addEventListener('submit', async (e) => {

&#x20;   e.preventDefault();

&#x20;   

&#x20;   const dateFrom = document.getElementById('dateFrom').value;

&#x20;   const dateTo = document.getElementById('dateTo').value;

&#x20;   

&#x20;   const data = await apiCall(`/api/invoices?from=${dateFrom}\&to=${dateTo}`);

&#x20;   

&#x20;   if (data) {

&#x20;       if (data.total\_count === 0) {

&#x20;           document.getElementById('emptyDiv').style.display = 'block';

&#x20;           document.getElementById('resultsDiv').style.display = 'none';

&#x20;       } else {

&#x20;           document.getElementById('emptyDiv').style.display = 'none';

&#x20;           document.getElementById('resultsDiv').style.display = 'block';

&#x20;           document.getElementById('totalCount').textContent = data.total\_count;

&#x20;           

&#x20;           const tbody = document.getElementById('invoicesTable');

&#x20;           tbody.innerHTML = '';

&#x20;           

&#x20;           data.invoices.forEach(invoice => {

&#x20;               const row = `

&#x20;                   <tr>

&#x20;                       <td>${invoice.id}</td>

&#x20;                       <td>${invoice.date}</td>

&#x20;                       <td>${invoice.amount.toLocaleString('vi-VN')} ₫</td>

&#x20;                       <td>${invoice.status}</td>

&#x20;                       <td>${invoice.issuer}</td>

&#x20;                       <td>

&#x20;                           <button class="btn btn-sm btn-info" onclick="downloadInvoice('${invoice.id}')">

&#x20;                               📥 Download

&#x20;                           </button>

&#x20;                       </td>

&#x20;                   </tr>

&#x20;               `;

&#x20;               tbody.innerHTML += row;

&#x20;           });

&#x20;           

&#x20;           document.getElementById('exportBtn').style.display = 'inline-block';

&#x20;           document.getElementById('exportBtn').onclick = () => {

&#x20;               window.location = `/api/export-excel?from=${dateFrom}\&to=${dateTo}`;

&#x20;           };

&#x20;       }

&#x20;   }

});



function downloadInvoice(invoiceId) {

&#x20;   window.location = `/api/invoices/${invoiceId}/download`;

}



document.getElementById('logoutBtn').addEventListener('click', async () => {

&#x20;   await apiCall('/api/auth/logout', {method: 'POST'});

&#x20;   window.location.href = '/login';

});

</script>

{% endblock %}

```



\*\*Output\*\*: Invoice search page works  

\*\*Status\*\*: ⬜ Not Started | 📝 In Progress | ✅ Complete



\---



\### Task 5.3 - Polish UI \& Styling

\*\*Dependency\*\*: Task 5.2  

\*\*Duration\*\*: 1-2 hours  

\*\*Description\*\*: Make interface professional



\*\*Update `static/css/style.css`\*\*:

```css

/\* Add responsive design, better spacing, etc. \*/

.table {

&#x20;   margin-top: 20px;

}



.btn {

&#x20;   min-width: 100px;

}



@media (max-width: 768px) {

&#x20;   .col-md-4 {

&#x20;       width: 100%;

&#x20;   }

}

```



\*\*Output\*\*: UI polished, responsive on mobile  

\*\*Status\*\*: ⬜ Not Started | 📝 In Progress | ✅ Complete



\---



\### ✅ CHECKPOINT 5: Frontend fully functional (login → search → download)



\---



\## PHASE 6: TESTING \& DEBUGGING



\### Task 6.1 - Run All Unit Tests

\*\*Dependency\*\*: Phase 5  

\*\*Duration\*\*: 1 hour  

\*\*Description\*\*: Verify all tests pass



\*\*Run\*\*: `pytest tests/ -v --cov=`  

\*\*Output\*\*: All tests passing, 70%+ coverage  

\*\*Status\*\*: ⬜ Not Started | 📝 In Progress | ✅ Complete



\---



\### Task 6.2 - Manual Testing Checklist

\*\*Dependency\*\*: Task 6.1  

\*\*Duration\*\*: 2-3 hours  

\*\*Description\*\*: Test all user scenarios



\*\*Checklist\*\*:

\- \[ ] Can login with valid credentials

\- \[ ] Cannot login with invalid credentials

\- \[ ] Date validation works (invalid format rejected)

\- \[ ] Search returns results

\- \[ ] Download single invoice works

\- \[ ] Export Excel works (file format correct)

\- \[ ] Session timeout works (30 min inactivity)

\- \[ ] Logout clears session

\- \[ ] Mobile responsive (check on narrow viewport)



\*\*Output\*\*: All scenarios tested, bugs logged  

\*\*Status\*\*: ⬜ Not Started | 📝 In Progress | ✅ Complete



\---



\### ✅ CHECKPOINT 6: All tests passing, all features working



\---



\## PHASE 7: DOCUMENTATION \& PACKAGING



\### Task 7.1 - Write README.md

\*\*Dependency\*\*: Phase 6  

\*\*Duration\*\*: 1 hour  

\*\*Description\*\*: Create project documentation



\*\*Create `README.md`\*\*:

```markdown

\# Invoice Download Webapp



\## What is this?

A local web app that simplifies downloading invoices from gdt.gov.vn



\## Quick Start



\### Prerequisites

\- Python 3.10+

\- pip



\### Installation

1\. Clone or download project

2\. Create venv: `python -m venv venv`

3\. Activate: `source venv/bin/activate` (Mac) or `venv\\Scripts\\activate` (Windows)

4\. Install: `pip install -r requirements.txt`

5\. Create .env file (copy from .env.example)

6\. Run: `python app.py`

7\. Open: http://localhost:5000



\## Usage

1\. Login with your gdt.gov.vn username/password

2\. Select date range

3\. Click "Tìm kiếm" to search

4\. Download individual invoices or export all to Excel



\## API Endpoints

\- POST /api/auth/login - User login

\- GET /api/invoices - Search invoices

\- GET /api/export-excel - Export to Excel

\- POST /api/auth/logout - Logout



\## Troubleshooting



\### "Không thể kết nối đến gdt.gov.vn"

\- Check internet connection

\- Try again in 5 minutes

\- Check if gdt.gov.vn is down



\### Excel file won't open

\- Download again

\- Try opening with Excel 2016+

\- Check file isn't corrupted



\## Support

Contact Huỳnh Anh Thuận

```



\*\*Output\*\*: README complete  

\*\*Status\*\*: ⬜ Not Started | 📝 In Progress | ✅ Complete



\---



\### Task 7.2 - Create API Documentation

\*\*Dependency\*\*: Task 7.1  

\*\*Duration\*\*: 1 hour  

\*\*Description\*\*: Document all API endpoints



\*\*Create `API\_SPEC.md`\*\* (comprehensive version)  

\*\*Output\*\*: API doc complete  

\*\*Status\*\*: ⬜ Not Started | 📝 In Progress | ✅ Complete



\---



\### Task 7.3 - Create SETUP Script

\*\*Dependency\*\*: Task 7.1  

\*\*Duration\*\*: 30 minutes  

\*\*Description\*\*: One-command setup



\*\*Create `setup.sh` (Mac/Linux)\*\*:

```bash

\#!/bin/bash

python -m venv venv

source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env

echo "Setup complete! Edit .env then run: python app.py"

```



\*\*Create `setup.bat` (Windows)\*\*:

```batch

python -m venv venv

call venv\\Scripts\\activate.bat

pip install -r requirements.txt

copy .env.example .env

echo Setup complete! Edit .env then run: python app.py

```



\*\*Output\*\*: Setup scripts ready  

\*\*Status\*\*: ⬜ Not Started | 📝 In Progress | ✅ Complete



\---



\### ✅ CHECKPOINT 7: Documentation complete, project ready to share



\---



\## 🎉 FINAL VERIFICATION



\*\*Project is COMPLETE when ALL are true\*\*:

\- ✅ Flask app runs without errors

\- ✅ Can login, search, download, export

\- ✅ 70%+ test coverage (pytest)

\- ✅ All manual tests pass

\- ✅ README + API docs complete

\- ✅ Setup script works

\- ✅ Code has docstrings

\- ✅ No credentials in code

\- ✅ Error messages are user-friendly

\- ✅ Ready to hand off



\---



\## 📊 Task Summary



\*\*Total Tasks\*\*: 21  

\*\*Estimated Time\*\*: 4-5 weeks  

\*\*Critical Path\*\*: Phase 3 → Phase 4 (API analysis blocks backend)



| Phase | Tasks | Time |

|-------|-------|------|

| 1: Setup | 2 | 1 day |

| 2: Learning | 3 | 3-5 days |

| 3: API Analysis | 3 | 5-7 days |

| 4: Backend | 6 | 7-10 days |

| 5: Frontend | 3 | 3-5 days |

| 6: Testing | 2 | 3-5 days |

| 7: Documentation | 3 | 2 days |



\---



\*\*Version\*\*: 1.0  

\*\*Created\*\*: 2026-05-19  

\*\*Next\*\*: Start PLAYBOOK 1 with `/speckit.implement`

