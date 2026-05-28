# website.py
from flask import Flask, render_template, url_for

app = Flask(__name__)

# 1. Route for the Homepage (The first page users see)
@app.route('/')
def home():
    return render_template('homepage.html')

# 2. Route for the Login Page (Matching url_for('login_page'))
@app.route('/login')
def login_page():
    return render_template('login.html')

# 3. Route for the Signup Page (Optional but recommended)
@app.route('/signup')
def register_page():
    return render_template('signup.html')

# 4. Route for the Report Page (Matching url_for('report'))
@app.route('/report')
def report():
    return render_template('report_page.html')

# Only one entry point for the application
if __name__ == '__main__':
    app.run(debug=True)