# website.py
import os
from flask import Flask, render_template, url_for, request, jsonify, redirect, flash, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone

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

@app.route('/login')
def login_page():
    return render_template('login.html')

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


# 6. 【地图标记专用接口】供主页 Homepage.html 用 Fetch 异步获取所有标记数据
@app.route('/api/get_all_reports', methods=['GET'])
def get_all_reports():
    try:
        reports = AnimalReport.query.all()
        report_list = []
        for r in reports:
            report_list.append({
                'id': r.id,
                'lat': r.latitude,
                'lng': r.longitude,
                'address': r.address if r.address else f"{r.latitude}, {r.longitude}",
                'animal_type': r.animal_type,
                'quantity': r.quantity,
                'health_status': r.health_status
            })
        return jsonify({'status': 'success', 'data': report_list})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

from sqlalchemy import and_

@app.route('/api/filter_reports', methods=['GET'])
def filter_reports():
    # 获取前端传来的多个勾选项（例如 ?types=cat,dog&healths=healthy）
    types_arg = request.args.get('types', '')
    healths_arg = request.args.get('healths', '')
    
    # 将字符串转为列表
    selected_types = types_arg.split(',') if types_arg else []
    selected_healths = healths_arg.split(',') if healths_arg else []
    
    query = AnimalReport.query
    
    # 如果用户选了，就执行数据库过滤
    if selected_types:
        query = query.filter(AnimalReport.animal_type.in_(selected_types))
    if selected_healths:
        query = query.filter(AnimalReport.health_status.in_(selected_healths))
        
    reports = query.all()
    
    # 转换为 JSON 返回
    return jsonify({
        'status': 'success',
        'data': [{
            'lat': r.latitude, 'lng': r.longitude,
            'animal_type': r.animal_type, 'health_status': r.health_status
        } for r in reports]
    })

@app.route('/settings')
def settings_page():
    return render_template('settings.html')
if __name__ == '__main__':
    app.run(debug=True)