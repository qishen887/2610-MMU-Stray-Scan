import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
# =================【Core Fix 1: Import Dependencies】=================
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'your_project_secret_key'  # Used for encryption Session

# =================【Core Fix 2: Configure and Initialize DB】=================
# Ensure it points to the location under the project root directory. reports.db

import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
print("====== Core Hint ======")
print("The absolute path of your code file is:", BASE_DIR)
print("The absolute path of the database Flask is looking for is:", os.path.join(BASE_DIR, "reports.db"))
print("======================")

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "reports.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# =================【Core Fix 3: Map Your Existing Database Tables】=================
class User(db.Model):
    # Must explicitly specify the table name as 'users' as seen in your tool
    __tablename__ = 'users'  
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    
    #  Core Hint: Since we cannot confirm if the 'role' column exists in your reports.db
    # 1. If you can see the 'role' column in your database viewer, keep the following line
    # 2. If your table【does not have】the 'role' column, comment out the following line
    role = db.Column(db.String(50), nullable=True, default='customer')


# --- Home route---
@app.route('/')
def show_login():
    if 'user' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    return render_template('login.html')

# --- Login handling ---
@app.route('/login', methods=['GET', 'POST'], endpoint='login_page')
def login():
    if request.method == 'GET':
        return render_template('login.html')

    email = request.form.get('email').lower().strip()
    password = request.form.get('password')

    # =================【Core Fix 4: Change to Query from Database】=================
    user_data = User.query.filter_by(email=email).first()

    # Validation logic: Use user_data.password instead of dictionary syntax
    if user_data and check_password_hash(user_data.password, password):
        session['user'] = email
        
        # Allocate/verify permissions based on email domain
        if email.endswith('@mmu.edu.my'):
            session['role'] = 'admin'
        else:
            # Compatibility handling: If the table contains a `role`, use the value from the table; otherwise, use the original default logic.
            session['role'] = getattr(user_data, 'role', 'customer') or 'customer'
        
        flash("Login successful!")
        
        if session['role'] == 'admin':
            flash(f"Welcome, {session['user']}! You are logged in as an administrator.")
            return redirect(url_for('admin_dashboard'))
        else:
            flash(f"Welcome, {session['user']}! You are logged in as a customer.")
            return redirect(url_for('user_dashboard'))
    else:
        flash("Invalid email or password. Please try again.")
        return redirect(url_for('show_login'))

# --- Admin-only page ---
@app.route('/admin-dashboard')
def admin_dashboard():
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied! Admins only.")
        return redirect(url_for('show_login'))
    return render_template('admin_page.html')

# --- Regular User Page ---
@app.route('/home')
def home_page():
    if 'user' not in session:
        flash("Please login first.")
        return redirect(url_for('show_login'))
    return render_template('Homepage.html')

@app.route('/user-dashboard')
def user_dashboard():
    if 'user' not in session:
        flash("Please login first.")
        return redirect(url_for('show_login'))
    return render_template('Homepage.html')

@app.route('/report', methods=['GET', 'POST'])
def report_page():
    if request.method == 'POST':
        flash("Report submitted successfully!")
        return redirect(url_for('user_dashboard'))
    return render_template('report_page.html')

@app.route('/vet-clinics')
def vet_clinics():
    return render_template('vets_clinics.html')

@app.route('/settings')
def settings_page():
    return render_template('settings.html')

@app.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('show_login'))

@app.route('/register', methods=['GET'])
def register_page():
    return render_template('signup.html')

# --- Registration handling ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')

    #  1. Capture the username passed from the frontend.
    username = request.form.get('username', '').strip() 
    email = request.form.get('email').lower().strip()
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    #  2. Add validation: Ensure username is not empty
    if not username or not email or not password:
        flash("Username, email and password are required.")
        return redirect(url_for('register_page'))

    if password != confirm_password:
        flash("Passwords do not match!")
        return redirect(url_for('register_page'))
    
    if not (len(password) == 8 and password.isdigit()):
        flash("Format error: Password must be exactly 8 digits!")
        return redirect(url_for('register_page'))
    
    if email.endswith('@mmu.edu.my'):
        user_role = 'admin'
    elif email.endswith('@student.mmu.edu.my'):
        user_role = 'customer'
    else:
        flash("Please use an official MMU email (@mmu.edu.my or @student.mmu.edu.my)")
        return redirect(url_for('register_page'))

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash("Email already registered. Please login.")
        return redirect(url_for('show_login'))

    #  3. Pass the username into the newly created user object.
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, email=email, password=hashed_password, role=user_role)
    
    db.session.add(new_user)
    db.session.commit()  # Write to the database

    flash("Registration successful! Please login.")
    return redirect(url_for('show_login'))

    

# --- forget password ---
@app.route('/forgot-password')
def forgot_password_page():
    return render_template('forgot_password.html')

@app.route('/reset-password', methods=['POST'])
def reset_password():
    email = request.form.get('email').lower().strip()
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    # =================【Core Fix 7: Query and modify the password in the database.】=================
    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Email address not found. Please register first.")
        return redirect(url_for('forgot_password_page'))

    if password != confirm_password:
        flash("Passwords do not match!")
        return redirect(url_for('forgot_password_page'))
    
    if not (len(password) == 8 and password.isdigit()):
        flash("Format error: Password must be exactly 8 digits!")
        return redirect(url_for('forgot_password_page'))

    # Change and save the password.
    user.password = generate_password_hash(password)
    db.session.commit()

    flash("Password reset successfully! Please login with your new password.")
    return redirect(url_for('show_login'))


if __name__ == '__main__':
    app.run(debug=True)