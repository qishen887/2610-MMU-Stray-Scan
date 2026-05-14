from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)

# Uploads folder 
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# SQLite database (saved next to report.py as reports.db)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'reports.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# Model
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
    status        = db.Column(db.String(20),  nullable=False, default='pending')  # pending/approved/rejected
    created_at    = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self):  #Return a JSON-serialisable dict for API responses.
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
            "status":        self.status,
            "created_at":    self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
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
def submit():  # Receive the form, save the image, write a row to the DB.
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
            saved_filename = file.filename
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
            status        = 'pending',
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


# Optional read endpoints for admin dashboard to list reports, view details, delete, or update status.

@app.route('/reports', methods=['GET'])
def get_reports(): #Return all reports, newest first.
    reports = AnimalReport.query.order_by(AnimalReport.created_at.desc()).all()
    return jsonify({"status": "success", "data": [r.to_dict() for r in reports]})


@app.route('/reports/<int:report_id>', methods=['GET'])
def get_report(report_id):  #Return a single report by ID.
    report = AnimalReport.query.get_or_404(report_id)
    return jsonify({"status": "success", "data": report.to_dict()})


@app.route('/reports/<int:report_id>', methods=['DELETE'])
def delete_report(report_id):   #Delete a report by ID.
    report = AnimalReport.query.get_or_404(report_id)
    db.session.delete(report)
    db.session.commit()
    return jsonify({"status": "success", "message": f"Report {report_id} deleted."})


@app.route('/admin')
def admin():
    return render_template('admin_page.html')


@app.route('/reports/<int:report_id>/status', methods=['PATCH'])
def update_status(report_id):   # Admin: change a report status to approved or rejected.
    try:
        report = AnimalReport.query.get_or_404(report_id)
        new_status = request.json.get('status')

        if new_status not in ('pending', 'approved', 'rejected'):
            return jsonify({"status": "error", "message": "Invalid status value."}), 400

        report.status = new_status
        db.session.commit()
        return jsonify({"status": "success", "data": report.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)})


@app.route('/export/excel')
def export_excel():
    import io
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from flask import send_file

    reports = AnimalReport.query.order_by(AnimalReport.created_at.desc()).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Animal Reports"

    # Header style
    header_font   = Font(bold=True, color="FFFFFF", name="Arial", size=11)
    header_fill   = PatternFill("solid", start_color="2E4057")
    header_align  = Alignment(horizontal="center", vertical="center")
    thin_border   = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin")
    )

    # Status fill colours
    status_fills = {
        "pending":  PatternFill("solid", start_color="FFF3CD"),
        "approved": PatternFill("solid", start_color="D4EDDA"),
        "rejected": PatternFill("solid", start_color="F8D7DA"),
    }
    status_fonts = {
        "pending":  Font(color="856404",  name="Arial", size=10),
        "approved": Font(color="155724",  name="Arial", size=10),
        "rejected": Font(color="721C24",  name="Arial", size=10),
    }

    headers = ["ID", "Animal", "Custom Animal", "Location", "Quantity",
               "Health Status", "Status", "Details", "Image", "Submitted At"]
    col_widths = [6, 16, 16, 24, 10, 14, 12, 36, 28, 22]

    # Write headers
    for col, (h, w) in enumerate(zip(headers, col_widths), 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font    = header_font
        cell.fill    = header_fill
        cell.alignment = header_align
        cell.border  = thin_border
        ws.column_dimensions[cell.column_letter].width = w

    ws.row_dimensions[1].height = 22

    # Write data rows
    row_fill_even = PatternFill("solid", start_color="F8F9FA")
    for r_idx, report in enumerate(reports, 2):
        row_data = [
            report.id,
            report.animal_type,
            report.custom_animal or "—",
            report.address,
            report.quantity,
            report.health_status,
            report.status,
            report.details or "—",
            report.image or "—",
            report.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        ]
        for c_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=r_idx, column=c_idx, value=value)
            cell.border    = thin_border
            cell.alignment = Alignment(vertical="center", wrap_text=(c_idx == 8))
            cell.font      = Font(name="Arial", size=10)
            if r_idx % 2 == 0:
                cell.fill = row_fill_even
            # Colour the status cell
            if c_idx == 7:
                s = report.status
                cell.fill = status_fills.get(s, PatternFill())
                cell.font = status_fonts.get(s, Font(name="Arial", size=10))
                cell.alignment = Alignment(horizontal="center", vertical="center")

        ws.row_dimensions[r_idx].height = 18

    # Summary row at the bottom
    last = len(reports) + 2
    ws.cell(row=last, column=1, value="Total").font = Font(bold=True, name="Arial", size=10)
    ws.cell(row=last, column=5, value=f'=SUM(E2:E{last-1})').font = Font(bold=True, name="Arial", size=10)

    # Freeze the header row
    ws.freeze_panes = "A2"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="animal_reports.xlsx"
    )


@app.route('/export/pdf')
def export_pdf():
    import io
    from flask import send_file
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.enums import TA_CENTER

    reports = AnimalReport.query.order_by(AnimalReport.created_at.desc()).all()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Title"],
                                 fontSize=16, spaceAfter=4, textColor=colors.HexColor("#2E4057"))
    sub_style   = ParagraphStyle("sub", parent=styles["Normal"],
                                 fontSize=9, textColor=colors.grey, spaceAfter=14)
    wrap_style  = ParagraphStyle("wrap", parent=styles["Normal"], fontSize=8, leading=10)

    story = [
        Paragraph("🐾 Animal Report Export", title_style),
        Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC  |  Total records: {len(reports)}", sub_style),
    ]

    # Table data
    col_headers = ["ID", "Animal", "Location", "Qty", "Health", "Status", "Details", "Submitted"]
    data = [col_headers]
    for rpt in reports:
        data.append([
            str(rpt.id),
            f"{rpt.custom_animal or rpt.animal_type}",
            rpt.address,
            str(rpt.quantity),
            rpt.health_status.capitalize(),
            rpt.status.capitalize(),
            Paragraph(rpt.details or "—", wrap_style),
            rpt.created_at.strftime("%Y-%m-%d\n%H:%M"),
        ])

    col_widths_pdf = [12*mm, 28*mm, 42*mm, 12*mm, 18*mm, 18*mm, 80*mm, 30*mm]

    STATUS_COLORS = {
        "pending":  colors.HexColor("#FFF3CD"),
        "approved": colors.HexColor("#D4EDDA"),
        "rejected": colors.HexColor("#F8D7DA"),
    }

    tbl = Table(data, colWidths=col_widths_pdf, repeatRows=1)
    base_style = [
        # Header
        ("BACKGROUND",  (0,0), (-1,0), colors.HexColor("#2E4057")),
        ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,0), 8),
        ("ALIGN",       (0,0), (-1,0), "CENTER"),
        ("BOTTOMPADDING",(0,0),(-1,0), 8),
        ("TOPPADDING",  (0,0), (-1,0), 8),
        # Body
        ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",    (0,1), (-1,-1), 8),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("GRID",        (0,0), (-1,-1), 0.4, colors.HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F8F9FA")]),
        ("ALIGN",       (0,1), (0,-1), "CENTER"),   # ID
        ("ALIGN",       (3,1), (3,-1), "CENTER"),   # Qty
        ("ALIGN",       (4,1), (5,-1), "CENTER"),   # Health / Status
        ("TOPPADDING",  (0,1), (-1,-1), 5),
        ("BOTTOMPADDING",(0,1),(-1,-1), 5),
    ]

    # Colour status cells per row
    for i, rpt in enumerate(reports, 1):
        bg = STATUS_COLORS.get(rpt.status, colors.white)
        base_style.append(("BACKGROUND", (5, i), (5, i), bg))

    tbl.setStyle(TableStyle(base_style))
    story.append(tbl)

    doc.build(story)
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf",
                     as_attachment=True, download_name="animal_reports.pdf")


if __name__ == '__main__':
    app.run(debug=True)
