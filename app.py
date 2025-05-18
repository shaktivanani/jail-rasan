from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime, timedelta
from models import StockInventory, db, RasanRecord, StockItem, ScaleEntry  # Make sure to import StockItem
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rasan.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/kedi')
def kedi():
    page = request.args.get('page', 1, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = RasanRecord.query.order_by(RasanRecord.date.desc())
    
    # Apply date filters if provided
    if start_date:
        query = query.filter(RasanRecord.date >= start_date)
    if end_date:
        query = query.filter(RasanRecord.date <= end_date)
    
    pagination = query.paginate(page=page, per_page=10)
    
    return render_template('kedi/list.html',
                         records=pagination.items,
                         pagination=pagination)


@app.route('/kedi/add', methods=['GET', 'POST'])
def add_kedi():
    if request.method == 'POST':
        date_str = request.form['date']
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Check if record for this date already exists
            if RasanRecord.query.filter_by(date=date).first():
                flash('A record for this date already exists!', 'danger')
                return redirect(url_for('add_kedi'))
            
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
            return redirect(url_for('kedi'))
        except ValueError:
            flash('Invalid date or number format!', 'danger')
    
    return render_template('kedi/add.html')

@app.route('/kedi/edit/<int:id>', methods=['GET', 'POST'])
def edit_kedi(id):
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
            return redirect(url_for('kedi'))
        except ValueError:
            flash('Invalid number format!', 'danger')
    
    return render_template('kedi/edit.html', record=record)

@app.route('/kedi/delete/<int:id>')
def delete_kedi(id):
    record = RasanRecord.query.get_or_404(id)
    db.session.delete(record)
    db.session.commit()
    flash('Record deleted successfully!', 'success')
    return redirect(url_for('kedi'))

# Stock Items CRUD
@app.route('/stock_items')
def stock_items():
    items = StockItem.query.order_by(StockItem.item_name).all()
    return render_template('stock_items/list.html', items=items)

@app.route('/stock_items/add', methods=['GET', 'POST'])
def add_stock_item():
    if request.method == 'POST':
        try:
            item = StockItem(
                item_name=request.form['item_name'],
                description=request.form.get('description', ''),
                unit=request.form['unit']
            )
            db.session.add(item)
            db.session.commit()
            flash('Stock item added successfully!', 'success')
            return redirect(url_for('stock_items'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('stock_items/add.html')

@app.route('/stock_items/edit/<int:id>', methods=['GET', 'POST'])
def edit_stock_item(id):
    item = StockItem.query.get_or_404(id)
    if request.method == 'POST':
        try:
            item.item_name = request.form['item_name']
            item.description = request.form.get('description', '')
            item.unit = request.form['unit']
            db.session.commit()
            flash('Stock item updated successfully!', 'success')
            return redirect(url_for('stock_items'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('stock_items/edit.html', item=item)

@app.route('/stock_items/delete/<int:id>')
def delete_stock_item(id):
    item = StockItem.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Stock item deleted successfully!', 'success')
    return redirect(url_for('stock_items'))

# Stock Inventory CRUD
@app.route('/stock_inventory')
def stock_inventory():
    page = request.args.get('page', 1, type=int)
    item_id = request.args.get('item_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = StockInventory.query.order_by(StockInventory.date.desc())
    
    # Apply filters
    if item_id:
        query = query.filter_by(stock_item_id=item_id)
        selected_item = StockItem.query.get(item_id)
    else:
        selected_item = None
        
    if start_date:
        query = query.filter(StockInventory.date >= start_date)
    if end_date:
        query = query.filter(StockInventory.date <= end_date)
    
    pagination = query.paginate(page=page, per_page=10)
    all_items = StockItem.query.order_by(StockItem.item_name).all()
    
    return render_template('stock_inventory/list.html',
                         inventory=pagination.items,
                         pagination=pagination,
                         all_items=all_items,
                         selected_item=selected_item)
@app.route('/stock_inventory/add', methods=['GET', 'POST'])
def add_stock_inventory():
    stock_items = StockItem.query.order_by(StockItem.item_name).all()
    
    if request.method == 'POST':
        try:
            entry = StockInventory(
                stock_item_id=int(request.form['stock_item']),
                quantity=float(request.form['quantity']),
                date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
                notes=request.form.get('notes', '')
            )
            db.session.add(entry)
            db.session.commit()
            flash('Stock entry added successfully!', 'success')
            return redirect(url_for('stock_inventory'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('stock_inventory/add.html', stock_items=stock_items)

@app.route('/stock_inventory/edit/<int:id>', methods=['GET', 'POST'])
def edit_stock_inventory(id):
    entry = StockInventory.query.get_or_404(id)
    stock_items = StockItem.query.order_by(StockItem.item_name).all()
    
    if request.method == 'POST':
        try:
            entry.stock_item_id = int(request.form['stock_item'])
            entry.quantity = float(request.form['quantity'])
            entry.date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
            entry.notes = request.form.get('notes', '')
            db.session.commit()
            flash('Stock entry updated successfully!', 'success')
            return redirect(url_for('stock_inventory'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('stock_inventory/edit.html', entry=entry, stock_items=stock_items)

@app.route('/stock_inventory/delete/<int:id>')
def delete_stock_inventory(id):
    entry = StockInventory.query.get_or_404(id)
    db.session.delete(entry)
    db.session.commit()
    flash('Stock entry deleted successfully!', 'success')
    return redirect(url_for('stock_inventory'))

@app.route('/stock_inventory/item/<int:item_id>')
def stock_inventory_by_item(item_id):
    item = StockItem.query.get_or_404(item_id)
    inventory = StockInventory.query.filter_by(stock_item_id=item_id)\
                   .order_by(StockInventory.date.desc())\
                   .all()
    return render_template('stock_inventory/list_by_item.html', 
                         inventory=inventory, 
                         item=item)
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

@app.route('/item_summary', methods=['GET', 'POST'])
def item_summary():
    if request.method == 'POST':
        try:
            stock_item_id = int(request.form['stock_item'])
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
            
            # Get the selected item
            stock_item = StockItem.query.get_or_404(stock_item_id)
            
            # Get all scale entries for this item in date range
            scale_entries = ScaleEntry.query.filter(
                ScaleEntry.stock_item_id == stock_item_id,
                ScaleEntry.start_date <= end_date,
                ScaleEntry.end_date >= start_date
            ).all()
            
            # Get all rasan records in date range
            rasan_records = RasanRecord.query.filter(
                RasanRecord.date.between(start_date, end_date)
                .order_by(RasanRecord.date.asc())
                .all())
            
            # Get all stock entries for this item in date range
            stock_entries = StockInventory.query.filter(
                StockInventory.stock_item_id == stock_item_id,
                StockInventory.date.between(start_date, end_date)
            ).all()
            
            # Create date range
            date_range = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
            
            # Calculate daily stock movements
            report_data = []
            opening_stock = stock_item.quantity  # Initial stock from item definition
            
            for date in date_range:
                # Find stock additions for this date
                daily_stock = sum(entry.quantity for entry in stock_entries if entry.date == date)
                total_stock = opening_stock + daily_stock
                
                # Find scale for this date
                scale_entry = next((entry for entry in scale_entries 
                                  if entry.start_date <= date <= entry.end_date), None)
                
                # Find rasan record for this date
                rasan_record = next((r for r in rasan_records if r.date == date), None)
                
                # Calculate values
                day_name = date.strftime('%A')
                
                if rasan_record:
                    kedi_total = rasan_record.kedi_total() - rasan_record.tifin_total() - rasan_record.medical_total()
                    scale_value = getattr(scale_entry, day_name.lower(), 0) if scale_entry else 0
                    used_stock = kedi_total * scale_value
                    closing_stock = total_stock - used_stock
                else:
                    kedi_total = 0
                    scale_value = 0
                    used_stock = 0
                    closing_stock = total_stock
                
                report_data.append({
                    'date': date,
                    'day_name': day_name,
                    'opening': opening_stock,
                    'income': daily_stock,
                    'total_stock': total_stock,
                    'kedi_total': kedi_total,
                    'scale_value': scale_value,
                    'used_stock': used_stock,
                    'closing': closing_stock
                })
                
                opening_stock = closing_stock
            
            return render_template('item_summary_report.html',
                                 report_data=report_data,
                                 stock_item=stock_item,
                                 start_date=start_date,
                                 end_date=end_date)
            
        except Exception as e:
            flash(f'Error generating report: {str(e)}', 'danger')
            return redirect(url_for('item_summary'))
    
    stock_items = StockItem.query.order_by(StockItem.item_name).all()
    return render_template('item_summary_form.html', stock_items=stock_items)


if __name__ == '__main__':
    app.run(debug=True)