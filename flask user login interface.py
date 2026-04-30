from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_project_secret_key'  # Must be set to encrypt the session

users = {
    "admin@example.com": {
        "password": generate_password_hash("admin123"), 
        "role": "admin"
    },
    "user@example.com": {
        "password": generate_password_hash("user123"), 
        "role": "customer"
    }
}

@app.route('/')
def index():
    # # If the user is already logged in, send him to the backend directly without logging in again.
    if 'user' in session:
        if session['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    # 1. Check if the email exists
    user_data = users.get(email)

    # 2. Validation logic
    # check_password_hash will automatically compare: the plaintext entered by the user vs the hashed code in the database
    if user_data and check_password_hash(user_data['password'], password):
        # Verification successful, record Session
        session['user'] = email
        session['role'] = user_data['role']
        
        flash("Login successful! feedback.")
        if session['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))
    else:
        # Authentication failed
        flash("Invalid email or password. Please try again.")
        return redirect(url_for('index'))

@app.route('/admin_dashboard')
def admin_dashboard():
    # Simple permission check: must be logged in and role is admin
    if session.get('role') == 'admin':
        return "<h1>Administrator backend</h1><p>Here you can manage animal report data.</p><a href='/logout'>Logout</a>"
    return redirect(url_for('index'))

@app.route('/user_dashboard')
def user_dashboard():
    # Simple permission check: must be logged in and role is customer
    if session.get('role') == 'customer':
        return "<h1>Customer Center</h1><p>You can submit new findings here.</p><a href='/logout'>Logout</a>"
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear() # Clear all login status
    return redirect(url_for('index'))

@app.route('/register')
def register_page():
    return render_template('signup.html') # 确保你有一个 signup.html 文件

if __name__ == '__main__':
    app.run(debug=True)