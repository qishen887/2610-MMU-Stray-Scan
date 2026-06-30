# website.py
import os
from flask import Flask, render_template, url_for, request, jsonify, redirect, flash, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash, check_password_hash
app = Flask(__name__)
app.secret_key = 'mmu'  # 保持和你原本 report_page.py 一致的密钥

# Uploads folder 
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 1. 配置数据库路径 (让程序在本地生成 reports.db)
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
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

def utc_now():
    return datetime.now(timezone.utc) + timedelta(hours=8)  # Adjust if you want a different timezone

# 2. 定义你的动物报告数据库表模型 (AnimalReport)
class AnimalReport(db.Model):
    __tablename__ = 'animals_reports'

    id            = db.Column(db.Integer, primary_key=True)
    animal_type   = db.Column(db.String(50),  nullable=False)   # value from dropdown
    custom_animal = db.Column(db.String(100), nullable=True)    # free-text if "other"
    address       = db.Column(db.String(500), nullable=True)   # typed or reverse-geocoded address
    latitude      = db.Column(db.Float, nullable=True)
    longitude     = db.Column(db.Float, nullable=True)
    quantity      = db.Column(db.Integer,     nullable=False)
    health_status = db.Column(db.String(20),  nullable=False)   # healthy/injured/sick/unknown
    details       = db.Column(db.Text,        nullable=True)
    image         = db.Column(db.String(255), nullable=True)    # stored filename only
    status        = db.Column(db.String(20),  nullable=False, default='pending')  # pending/approved/rejected
    created_at    = db.Column(db.DateTime,    default=utc_now)
    submitted_by_email = db.Column(db.String(120), nullable=True)  # None = guest submission

    def to_dict(self):  #Return a JSON-serialisable dict for API responses.
        return {
            "id":            self.id,
            "animal":        self.custom_animal if self.custom_animal else self.animal_type,
            "animal_type":   self.animal_type,
            "custom_animal": self.custom_animal,
            "location":      self.address or (f"{self.latitude}, {self.longitude}" if self.latitude else "—"),
            "quantity":      self.quantity,
            "health":        self.health_status,
            "details":       self.details,
            "image":         self.image if self.image else None,
            "status":        self.status,
            "created_at":    self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "submitted_by":  self.submitted_by_email or "Guest",
        }
    
# 3. 确保在程序启动时，数据库和表能在本地自动创建好
with app.app_context():
    db.create_all()

# Routes
app.secret_key = 'mmu'  # same key as in the login file
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# 4. 原有的基础页面路由
@app.route('/')
def home():
    return render_template('homepage.html')

@app.route('/home')
def homepage():
    return render_template('homepage.html')

@app.route('/login', methods=['GET', 'POST'])
def show_login():
    if request.method == 'GET':
        if 'user' in session:
            return redirect(url_for('homepage'))
        return render_template('login.html')

    email = (request.form.get('email') or '').strip().lower()
    password = request.form.get('password') or ''

    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password, password):
        session['user'] = user.email
        session['role'] = user.role or 'customer'
        session['display_name'] = user.email.split('@')[0]
        return redirect(url_for('homepage'))

    flash("Invalid email or password. Please try again.")
    return redirect(url_for('show_login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('show_login'))

@app.route('/session-info')
def session_info():
    if 'user' in session:
        return jsonify({
            "logged_in": True,
            "email": session['user'],
            "role": session.get('role', 'customer'),
            "display_name": session.get('display_name') or session['user'].split('@')[0],
        })
    return jsonify({"logged_in": False})

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/submit', methods=['POST'])
def submit():  # Receive the form, save the image, write a row to the DB.
    try:
        animal_type   = request.form.get('animalType')
        custom_animal = request.form.get('customAnimal') or None
        address       = request.form.get('address') or None
        latitude      = request.form.get('latitude')
        longitude     = request.form.get('longitude')
        quantity      = request.form.get('quantity')
        health_status = request.form.get('healthStatus')
        details       = request.form.get('details') or None

        # Save uploaded image
        file = request.files.get('img')
        saved_filename = None
        if file and file.filename != '':
            saved_filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], saved_filename))

        # Insert into database 
        report = AnimalReport(
            animal_type   = animal_type,
            custom_animal = custom_animal,
            address       = address,
            latitude      = float(request.form.get('latitude')) if request.form.get('latitude') else None,
            longitude     = float(request.form.get('longitude')) if request.form.get('longitude') else None,
            quantity      = int(quantity),
            health_status = health_status,
            details       = details,
            image         = saved_filename,
            status        = 'pending',
            submitted_by_email = session.get('user'),  # None if not logged in
        )
        db.session.add(report)
        db.session.commit()

        print(f"[DB] Saved report id={report.id}")

        return jsonify({
            "status":  "success",
            "message": "Report submitted successfully",
            "data":    report.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] {e}")
        return jsonify({"status": "error", "message": str(e)})


# 5. 【关键修改】报告页面路由：同时允许 GET（打开页面）和 POST（提交表单）
@app.route('/report', methods=['GET', 'POST'])
def report():
    if request.method == 'POST':
        try:
            # 从前端 report_page.html 的表单里抓取用户填的数据
            animal_type = request.form.get('animal_type')
            quantity = request.form.get('quantity')
            health_status = request.form.get('health_status')
            lat = request.form.get('latitude')
            lng = request.form.get('longitude')
            address = request.form.get('address')
            
            # 创建一条新的数据库记录（注意检查每行末尾的逗号！）
            new_report = AnimalReport(
                animal_type=animal_type,
                quantity=int(quantity),
                health_status=health_status,
                latitude=float(lat),
                longitude=float(lng),
                address=address
            )
            
            # 保存到 SQLite 数据库文件中
            db.session.add(new_report)
            db.session.commit()
            
            flash('Report submitted successfully!', 'success')
            return redirect(url_for('home'))  # 提交成功后跳回主页看地图标记
            
        except Exception as e:
            db.session.rollback()
            return f"Database Error: {str(e)}", 500

    # 如果是普通的打开网页（GET 请求），直接渲染 HTML
    return render_template('report_page.html')

@app.route('/vet-clinics')
@app.route('/vets_clinics')
def vet_clinics():
    return render_template('vets_clinics.html', form_mode=None, edit_clinic=None, clinics=[])


@app.route('/vet-clinics/add', methods=['GET', 'POST'])
def add_vet_clinic():
    if request.method == 'POST':
        flash('Vet clinic submission is not enabled in this build yet.', 'warning')
        return redirect(url_for('vet_clinics'))
    return render_template('vets_clinics.html', form_mode='add', edit_clinic=None, clinics=[])


@app.route('/vet-clinics/<int:clinic_id>/edit', methods=['GET', 'POST'])
def edit_vet_clinic(clinic_id):
    if request.method == 'POST':
        flash('Vet clinic editing is not enabled in this build yet.', 'warning')
        return redirect(url_for('vet_clinics'))
    return render_template('vets_clinics.html', form_mode='edit', edit_clinic={'id': clinic_id, 'name': '', 'phone': '', 'address': '', 'operating_hours': '', 'google_map_link': '', 'latitude': None, 'longitude': None, 'image': None}, clinics=[])


@app.route('/vet-clinics/<int:clinic_id>/delete', methods=['POST'])
def delete_vet_clinic(clinic_id):
    flash('Vet clinic deletion is not enabled in this build yet.', 'warning')
    return redirect(url_for('vet_clinics'))

from sqlalchemy import and_

@app.route('/api/get_all_reports', methods=['GET'])
def get_all_reports():
    try:
        # Get the filter query parameter sent from the frontend (e.g., 'cat', 'dog')
        animal_type_query = request.args.get('animal_type', '')

        # Filter the database query if a specific animal type is selected and not 'all'
        if animal_type_query and animal_type_query != 'all':
            reports = AnimalReport.query.filter_by(animal_type=animal_type_query).all()
        else:
            # Fallback to retrieving all reports if no filter or 'all' is requested
            reports = AnimalReport.query.all()

        report_list = []
        for r in reports:
            # Safely generate the image static access link if an image file exists in the database
            img_url = url_for('uploaded_file', filename=r.image) if getattr(r, 'image', None) else None
            
            # Pack database record values into a standard data dictionary format
            report_list.append({
                'id': r.id,
                'lat': r.latitude,
                'lng': r.longitude,
                'address': r.address if r.address else f"{r.latitude}, {r.longitude}",
                'animal_type': r.animal_type,
                'quantity': r.quantity,
                'health_status': r.health_status,
                'image_url': img_url
            })
        return jsonify({'status': 'success', 'data': report_list})
    except Exception as e:
        # Return internal server error message if database tracking fails
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
@app.route('/api/filter_reports', methods=['GET'])
def filter_reports():
    """
    API endpoint to filter animal reports based on user selection.
    Expects URL query parameters like: ?types=dog,cat&healths=healthy,injured
    """
    try:
        # 1. Retrieve query parameters from the frontend request
        types_param = request.args.get('types', '')
        healths_param = request.args.get('healths', '')
        
        # 2. Start with a base query that selects all reports
        query = AnimalReport.query
        
        # 3. Apply the Animal Type filter if the user selected any
        if types_param:
            # Convert comma-separated string into a Python list: ['dog', 'cat']
            type_list = types_param.split(',')
            # Use SQLAlchemy's .in_() to filter rows matching any type in the list
            query = query.filter(AnimalReport.animal_type.in_(type_list))
            
        # 4. Apply the Health Status filter if the user selected any
        if healths_param:
            health_list = healths_param.split(',')
            query = query.filter(AnimalReport.health_status.in_(health_list))
            
        # 5. Execute the query to fetch the filtered results from the database
        filtered_reports = query.all()
        
        # 6. Format the database objects into a list of dictionaries for JSON response
        report_list = []
        for r in filtered_reports:
            img_url = url_for('uploaded_file', filename=r.image) if getattr(r, 'image', None) else None
            report_list.append({
                'id': r.id,
                'lat': r.latitude,
                'lng': r.longitude,
                'address': r.address if r.address else f"{r.latitude}, {r.longitude}",
                'animal_type': r.animal_type,
                'quantity': getattr(r, 'quantity', 1), # Default to 1 if not exist
                'health_status': r.health_status,
                'image_url': img_url
            })
            
        # 7. Return the successful response back to the frontend
        return jsonify({'status': 'success', 'data': report_list})

    except Exception as e:
        # Return error details if something goes wrong
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/settings')
def settings_page():
    return render_template('settings.html')

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
from flask import send_from_directory, url_for

if __name__ == '__main__':
    app.run(debug=True)
