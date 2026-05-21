from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_project_secret_key'  # Must be set to encrypt the session


users = {
    "admin@student.mmu.edu.my": {
        "password": generate_password_hash("admin123"), 
        "role": "admin"
    },
    "user@student.mmu.edu.my": {
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


@app.route('/signup', methods=['POST'])
def signup():
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    # 1. 基础验证
    if not email or not password:
        flash("Email and password are required.")
        return redirect(url_for('register_page'))

    if password != confirm_password:
        flash("Passwords do not match!")
        return redirect(url_for('register_page'))
    
# 2. 验证是否为 8 位数字
    # .isdigit() 检查是否全是数字，len() 检查长度
    if not (len(password) == 8):
        flash("Format error: Password must be exactly 8 digits!")
        return redirect(url_for('register_page'))
    
  # --- 核心逻辑：根据后缀分配角色 ---
    if email.endswith('@mmu.edu.my'):
        user_role = 'admin'
    elif email.endswith('@student.mmu.edu.my'):
        user_role = 'customer'
    else:
        # 如果后缀都不对，拒绝注册
        flash("Please use an official MMU email (@mmu.edu.my or @student.mmu.edu.my)")
        return redirect(url_for('register_page'))
        

    # 2. 检查用户是否已存在
    if email in users:
        flash("Email already registered. Please login.")
        return redirect(url_for('index'))

    # 3. 哈希加密密码并存储 (默认角色设为 customer)
    hashed_password = generate_password_hash(password)
    users[email] = {
        "password": hashed_password,
        "role": "customer"
    }

    flash("Registration successful! Please login.")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)