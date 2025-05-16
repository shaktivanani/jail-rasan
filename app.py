from flask import Flask, render_template, request, redirect, url_for, flash
from flask_bootstrap import Bootstrap
from datetime import datetime, timedelta
from models import db, RasanRecord, StockItem, ScaleEntry  # Make sure to import StockItem
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

@app.route('/stock')
def stock_list():
    items = StockItem.query.order_by(StockItem.date.desc()).all()
    return render_template('stock/stock_list.html', items=items)

@app.route('/stock/add', methods=['GET', 'POST'])
def add_stock():
    if request.method == 'POST':
        try:
            date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
            item = StockItem(
                date=date,
                item_name=request.form['item_name'],
                quantity=float(request.form['quantity']),
                unit=request.form['unit'],
                notes=request.form.get('notes', '')
            )
            
            db.session.add(item)
            db.session.commit()
            flash('Stock item added successfully!', 'success')
            return redirect(url_for('stock_list'))
        except ValueError:
            flash('Invalid date or quantity format!', 'danger')
    
    return render_template('stock/add_stock.html')

@app.route('/stock/edit/<int:id>', methods=['GET', 'POST'])
def edit_stock(id):
    item = StockItem.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            item.date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
            item.item_name = request.form['item_name']
            item.quantity = float(request.form['quantity'])
            item.unit = request.form['unit']
            item.notes = request.form.get('notes', '')
            
            db.session.commit()
            flash('Stock item updated successfully!', 'success')
            return redirect(url_for('stock_list'))
        except ValueError:
            flash('Invalid date or quantity format!', 'danger')
    
    return render_template('stock/edit_stock.html', item=item)

@app.route('/stock/delete/<int:id>')
def delete_stock(id):
    item = StockItem.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Stock item deleted successfully!', 'success')
    return redirect(url_for('stock_list'))

@app.route('/scale')
def scale_list():
    entries = ScaleEntry.query.all()
    return render_template('scale/scale_list.html', entries=entries)

@app.route('/scale/add', methods=['GET', 'POST'])
def add_scale():
    stock_items = StockItem.query.all()
    
    if request.method == 'POST':
        try:
            stock_item_id = int(request.form['stock_item'])
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
            
            # Check for overlapping entries
            overlap = ScaleEntry.query.filter(
                ScaleEntry.stock_item_id == stock_item_id,
                ScaleEntry.start_date <= end_date,
                ScaleEntry.end_date >= start_date
            ).first()
            
            if overlap:
                flash('This item already has a scale entry for the selected date range!', 'danger')
                return redirect(url_for('add_scale'))
            
            entry = ScaleEntry(
                stock_item_id=stock_item_id,
                start_date=start_date,
                end_date=end_date,
                monday=float(request.form['monday']),
                tuesday=float(request.form['tuesday']),
                wednesday=float(request.form['wednesday']),
                thursday=float(request.form['thursday']),
                friday=float(request.form['friday']),
                saturday=float(request.form['saturday']),
                sunday=float(request.form['sunday'])
            )
            
            db.session.add(entry)
            db.session.commit()
            flash('Scale entry added successfully!', 'success')
            return redirect(url_for('scale_list'))
            
        except ValueError:
            flash('Invalid data format!', 'danger')
    
    return render_template('scale/add_scale.html', stock_items=stock_items)

@app.route('/scale/edit/<int:id>', methods=['GET', 'POST'])
def edit_scale(id):
    entry = ScaleEntry.query.get_or_404(id)
    stock_items = StockItem.query.all()
    
    if request.method == 'POST':
        try:
            # Check for overlapping entries excluding current entry
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
            
            overlap = ScaleEntry.query.filter(
                ScaleEntry.stock_item_id == entry.stock_item_id,
                ScaleEntry.id != entry.id,
                ScaleEntry.start_date <= end_date,
                ScaleEntry.end_date >= start_date
            ).first()
            
            if overlap:
                flash('This item already has a scale entry for the selected date range!', 'danger')
                return redirect(url_for('edit_scale', id=id))
            
            entry.start_date = start_date
            entry.end_date = end_date
            entry.monday = float(request.form['monday'])
            entry.tuesday = float(request.form['tuesday'])
            entry.wednesday = float(request.form['wednesday'])
            entry.thursday = float(request.form['thursday'])
            entry.friday = float(request.form['friday'])
            entry.saturday = float(request.form['saturday'])
            entry.sunday = float(request.form['sunday'])
            
            db.session.commit()
            flash('Scale entry updated successfully!', 'success')
            return redirect(url_for('scale_list'))
            
        except ValueError:
            flash('Invalid data format!', 'danger')
    
    return render_template('scale/edit_scale.html', entry=entry, stock_items=stock_items)

@app.route('/scale/delete/<int:id>')
def delete_scale(id):
    entry = ScaleEntry.query.get_or_404(id)
    db.session.delete(entry)
    db.session.commit()
    flash('Scale entry deleted successfully!', 'success')
    return redirect(url_for('scale_list'))

@app.route('/stock_summary', methods=['GET', 'POST'])
def stock_summary():
    if request.method == 'POST':
        try:
            stock_item_id = int(request.form['stock_item'])
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
            
            # Get relevant data
            stock_item = StockItem.query.get(stock_item_id)
            scale_entries = ScaleEntry.query.filter(
                ScaleEntry.stock_item_id == stock_item_id,
                ScaleEntry.start_date <= end_date,
                ScaleEntry.end_date >= start_date
            ).all()
            
            rasan_records = RasanRecord.query.filter(
                RasanRecord.date.between(start_date, end_date)
            ).all()
            
            stock_entries = StockItem.query.filter(
                StockItem.id == stock_item_id,
                StockItem.date.between(start_date, end_date)
            ).all()
            
            # Create date range
            date_range = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
            
            # Calculate stock movements
            report_data = []
            opening_stock = stock_item.quantity  # Initial stock
            
            for date in date_range:
                # Get daily scale
                scale = next((entry for entry in scale_entries 
                            if entry.start_date <= date <= entry.end_date), None)
                
                # Get daily rasan record
                rasan = next((r for r in rasan_records if r.date == date), None)
                
                # Get daily stock additions
                daily_stock = sum(entry.quantity for entry in stock_entries if entry.date == date)
                
                # Calculate values
                total_stock = opening_stock + daily_stock
                kedi_total = (rasan.kedi_total() - rasan.tifin_total() - rasan.medical_total()) if rasan else 0
                used_stock = kedi_total * getattr(scale, date.strftime('%A').lower(), 0) if scale else 0
                closing_stock = total_stock - used_stock
                
                report_data.append({
                    'date': date,
                    'day_name': date.strftime('%A'),
                    'opening': opening_stock,
                    'income': daily_stock,
                    'total_stock': total_stock,
                    'kedi_total': kedi_total,
                    'scale': getattr(scale, date.strftime('%A').lower(), 0) if scale else 0,
                    'used_stock': used_stock,
                    'closing': closing_stock
                })
                
                opening_stock = closing_stock
                
            return render_template('stock_summary.html', 
                                 report_data=report_data,
                                 stock_item=stock_item)
            
        except Exception as e:
            flash(f'Error generating report: {str(e)}', 'danger')
    
    stock_items = StockItem.query.all()
    return render_template('stock_summary_form.html', stock_items=stock_items)

if __name__ == '__main__':
    app.run(debug=True)