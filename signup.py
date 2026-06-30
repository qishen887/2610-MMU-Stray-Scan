from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_project_secret_key'  # 必须设置，用于加密 Session

# 内存模拟数据库
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

# --- 修复点 1：首页路由函数改名为 show_login ---
@app.route('/')
def show_login():
    # 如果用户已经登录，直接送去对应的后台
    if 'user' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    return render_template('login.html')

# --- 修复点 2：处理登录提交的函数保持为 login ---
@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email').lower().strip()
    password = request.form.get('password')

    # 1. 检查账号是否存在
    user_data = users.get(email)

    # 2. 验证逻辑
    if user_data and check_password_hash(user_data['password'], password):
        session['user'] = email
        
        # 核心逻辑：根据邮箱后缀分配/校对权限
        if email.endswith('@mmu.edu.my'):
            session['role'] = 'admin'
        else:
            session['role'] = user_data.get('role', 'customer')
        
        flash("Login successful!")
        
        if session['role'] == 'admin':
            flash(f"Welcome, {session['user']}! You are logged in as an administrator.")
            return redirect(url_for('admin_dashboard'))
        else:
            flash(f"Welcome, {session['user']}! You are logged in as a customer.")
            return redirect(url_for('user_dashboard'))
    else:
        flash("Invalid email or password. Please try again.")
        return redirect(url_for('show_login')) # 修复：重定向回登录页

# --- Admin 专用页面 ---
@app.route('/admin-dashboard')
def admin_dashboard():
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied! Admins only.")
        return redirect(url_for('show_login')) # 修复：重定向回登录页
    return render_template('admin_page.html')

# --- 普通 User 页面 ---
@app.route('/user-dashboard')
def user_dashboard():
    if 'user' not in session:
        flash("Please login first.")
        return redirect(url_for('show_login')) # 修复：重定向回登录页
    return render_template('Homepage.html')

@app.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('show_login')) # 修复：重定向回登录页

@app.route('/register')
def register_page():
    return render_template('signup.html')

@app.route('/signup', methods=['POST'])
def signup():
    email = request.form.get('email').lower().strip()
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if not email or not password:
        flash("Email and password are required.")
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

    if email in users:
        flash("Email already registered. Please login.")
        return redirect(url_for('show_login')) # 修复：重定向回登录页

    hashed_password = generate_password_hash(password)
    users[email] = {
        "password": hashed_password,
        "role": user_role
    }

    flash("Registration successful! Please login.")
    return redirect(url_for('show_login')) # 修复：重定向回登录页

# --- 忘记密码 ---
@app.route('/forgot-password')
def forgot_password_page():
    return render_template('forgot_password.html')

@app.route('/reset-password', methods=['POST'])
def reset_password():
    email = request.form.get('email').lower().strip()
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if email not in users:
        flash("Email address not found. Please register first.")
        return redirect(url_for('forgot_password_page'))

    if password != confirm_password:
        flash("Passwords do not match!")
        return redirect(url_for('forgot_password_page'))
    
    if not (len(password) == 8 and password.isdigit()):
        flash("Format error: Password must be exactly 8 digits!")
        return redirect(url_for('forgot_password_page'))

    users[email]['password'] = generate_password_hash(password)

    flash("Password reset successfully! Please login with your new password.")
    return redirect(url_for('show_login'))  # 修复点 3：把不存在的 'index' 改为 'show_login'

if __name__ == '__main__':
    app.run(debug=True)