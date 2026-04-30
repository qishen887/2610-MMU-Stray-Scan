from ast import Return

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Uploads folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

#SQLite database (saved next to report.py as reports.db)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'reports.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


#Model
class AnimalReport(db.Model):
    __tablename__ = 'animal_reports'

    id            = db.Column(db.Integer, primary_key=True)
    animal_type   = db.Column(db.String(50),  nullable=False)   # value from dropdown
    custom_animal = db.Column(db.String(100), nullable=True)    # free-text if "other"
    address       = db.Column(db.String(255), nullable=False)
    quantity      = db.Column(db.Integer,     nullable=False)
    health_status = db.Column(db.String(20),  nullable=False)   # healthy/injured/sick/unknown
    details       = db.Column(db.Text,        nullable=True)
    image         = db.Column(db.String(255), nullable=True)    # stored filename only
    created_at    = db.Column(db.DateTime,    default=datetime.utcnow)
    status        = db.Column(db.String(20),  nullable=False, default='pending')  # pending first, then admin can change the status

    def to_dict(self):  # Return a JSON-serialisable dict for API responses.
        return {
            "id":            self.id,
            "animal":        self.custom_animal if self.custom_animal else self.animal_type,
            "animal_type":   self.animal_type,
            "custom_animal": self.custom_animal,
            "location":      self.address,
            "quantity":      self.quantity,
            "health":        self.health_status,
            "details":       self.details,
            "image":         self.image,
            "created_at":    self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "status":        self.status
        }


# Create all tables on first run
with app.app_context():
    db.create_all()


# Routes

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/')
def home():
    return render_template('report_page.html')


@app.route('/submit', methods=['POST'])
def submit():    # Receive the form, save the image, write a row to the DB.
    try:
        animal_type   = request.form.get('animalType')
        custom_animal = request.form.get('customAnimal') or None
        address       = request.form.get('address')
        quantity      = request.form.get('quantity')
        health_status = request.form.get('healthStatus')
        details       = request.form.get('details') or None

        # Save uploaded image 
        file = request.files.get('img')
        saved_filename = None
        if file and file.filename != '':
            saved_filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], saved_filename))

        # Insert into database
        report = AnimalReport(
            animal_type   = animal_type,
            custom_animal = custom_animal,
            address       = address,
            quantity      = int(quantity),
            health_status = health_status,
            details       = details,
            image         = saved_filename,
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


# Optional read endpoints

@app.route('/reports', methods=['GET'])
def get_reports(): # Return all reports, newest first.
    reports = AnimalReport.query.order_by(AnimalReport.created_at.desc()).all()
    return jsonify({"status": "success", "data": [r.to_dict() for r in reports]})


@app.route('/reports/<int:report_id>', methods=['GET'])
def get_report(report_id): # Return a single report by ID.
    report = AnimalReport.query.get_or_404(report_id)
    return jsonify({"status": "success", "data": report.to_dict()})


@app.route('/reports/<int:report_id>', methods=['DELETE'])
def delete_report(report_id): # Delete a report by ID.
    report = AnimalReport.query.get_or_404(report_id)
    db.session.delete(report)
    db.session.commit()
    return jsonify({"status": "success", "message": f"Report {report_id} deleted."})


if __name__ == '__main__':
    app.run(debug=True)
