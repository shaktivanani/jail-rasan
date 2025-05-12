from flask import Flask, render_template, request, redirect, url_for, flash
from flask_bootstrap import Bootstrap
from datetime import datetime
from models import db, RasanRecord
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rasan.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

bootstrap = Bootstrap(app)
db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    records = RasanRecord.query.order_by(RasanRecord.date.desc()).all()
    return render_template('index.html', records=records)

@app.route('/add', methods=['GET', 'POST'])
def add_record():
    if request.method == 'POST':
        date_str = request.form['date']
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Check if record for this date already exists
            if RasanRecord.query.filter_by(date=date).first():
                flash('A record for this date already exists!', 'danger')
                return redirect(url_for('add_record'))
            
            record = RasanRecord(
                date=date,
                kedi_m=int(request.form['kedi_m']),
                kedi_f=int(request.form['kedi_f']),
                tifin_m=int(request.form['tifin_m']),
                tifin_f=int(request.form['tifin_f']),
                medical_m=int(request.form['medical_m']),
                medical_f=int(request.form['medical_f'])
            )
            
            db.session.add(record)
            db.session.commit()
            flash('Record added successfully!', 'success')
            return redirect(url_for('index'))
        except ValueError:
            flash('Invalid date or number format!', 'danger')
    
    return render_template('add_record.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_record(id):
    record = RasanRecord.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            record.kedi_m = int(request.form['kedi_m'])
            record.kedi_f = int(request.form['kedi_f'])
            record.tifin_m = int(request.form['tifin_m'])
            record.tifin_f = int(request.form['tifin_f'])
            record.medical_m = int(request.form['medical_m'])
            record.medical_f = int(request.form['medical_f'])
            
            db.session.commit()
            flash('Record updated successfully!', 'success')
            return redirect(url_for('index'))
        except ValueError:
            flash('Invalid number format!', 'danger')
    
    return render_template('edit_record.html', record=record)

@app.route('/delete/<int:id>')
def delete_record(id):
    record = RasanRecord.query.get_or_404(id)
    db.session.delete(record)
    db.session.commit()
    flash('Record deleted successfully!', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)