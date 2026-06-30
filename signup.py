import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
# =================【核心修复 1：引入依赖】=================
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'your_project_secret_key'  # 用于加密 Session

# =================【核心修复 2：配置并初始化 DB】=================
# 确保指向项目根目录下的 reports.db

import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
print("====== 核心提示 ======")
print("你的代码文件所在的绝对路径是:", BASE_DIR)
print("Flask 正在寻找的数据库绝对路径是:", os.path.join(BASE_DIR, "reports.db"))
print("======================")

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "reports.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# =================【核心修复 3：映射你现有的数据库表】=================
class User(db.Model):
    # 必须显式指定表名为你在工具里看到的 'users'
    __tablename__ = 'users'  
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    
    # 💡 提示：由于无法确认你的 reports.db 里有没有 role 这一列
    # 1. 如果你在查看器右侧能看到 role 列，请保留下面这行
    # 2. 如果你的表里【确实没有】role 列，请把下面这行注释掉
    role = db.Column(db.String(50), nullable=True, default='customer')


# --- 首页路由 ---
@app.route('/')
def show_login():
    if 'user' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    return render_template('login.html')

# --- 登录处理 ---
@app.route('/login', methods=['GET', 'POST'], endpoint='login_page')
def login():
    if request.method == 'GET':
        return render_template('login.html')

    email = request.form.get('email').lower().strip()
    password = request.form.get('password')

    # =================【核心修复 4：改为从数据库查询】=================
    user_data = User.query.filter_by(email=email).first()

    # 验证逻辑：使用 user_data.password 代替字典写法
    if user_data and check_password_hash(user_data.password, password):
        session['user'] = email
        
        # 根据邮箱后缀分配/校对权限
        if email.endswith('@mmu.edu.my'):
            session['role'] = 'admin'
        else:
            # 兼容处理：如果表里有role就用表里的，没有就用原本的默认逻辑
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

# --- Admin 专用页面 ---
@app.route('/admin-dashboard')
def admin_dashboard():
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied! Admins only.")
        return redirect(url_for('show_login'))
    return render_template('admin_page.html')

# --- 普通 User 页面 ---
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

# --- 注册处理 ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')

    # 👈 1. 抓取前端传过来的 username
    username = request.form.get('username', '').strip() 
    email = request.form.get('email').lower().strip()
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    # 👈 2. 增加校验：确保用户名不为空
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

    # 👈 3. 将 username 传进新创建的用户对象中
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, email=email, password=hashed_password, role=user_role)
    
    db.session.add(new_user)
    db.session.commit()  # 写入数据库

    flash("Registration successful! Please login.")
    return redirect(url_for('show_login'))

    

# --- 忘记密码 ---
@app.route('/forgot-password')
def forgot_password_page():
    return render_template('forgot_password.html')

@app.route('/reset-password', methods=['POST'])
def reset_password():
    email = request.form.get('email').lower().strip()
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    # =================【核心修复 7：从数据库查询并修改密码】=================
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

    # 修改密码并保存
    user.password = generate_password_hash(password)
    db.session.commit()

    flash("Password reset successfully! Please login with your new password.")
    return redirect(url_for('show_login'))


if __name__ == '__main__':
    app.run(debug=True)