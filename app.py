import os
import secrets
from unittest import result
from flask import Flask, render_template, request, flash, redirect, url_for, session, send_file
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from models import db, StockItem, StockInventory, ScaleEntry, RasanRecord
import pandas as pd
from io import BytesIO
from export import ReportExporter

# Initialize Flask application
app = Flask(__name__)

# Configure application settings
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')  # Secret key for session management
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rasan.db'  # Database URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable modification tracking
db.init_app(app)  # Initialize SQLAlchemy with Flask app

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

# Helper function to apply date filters to queries (not implemented in this snippet)
def get_date_filters(query):
    return query

# Route for the home page
@app.route('/')
def index():
    return render_template('index.html')

# Routes for KEDI (Kitchen and Dining) management
@app.route('/kedi')
def kedi():
    # Paginate KEDI records with 10 items per page
    page = request.args.get('page', 1, type=int)
    query = get_date_filters(RasanRecord).order_by(RasanRecord.date.desc())
    pagination = query.paginate(page=page, per_page=10)
    return render_template('kedi/list.html',
                         records=pagination.items,
                         pagination=pagination)

@app.route('/kedi/add', methods=['GET', 'POST'])
def add_kedi():
    if request.method == 'POST':
        try:
            # Parse and validate date
            date_str = request.form['date']
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Check for duplicate records for the same date
            if RasanRecord.query.filter_by(date=date).first():
                flash('A record for this date already exists!', 'danger')
                return redirect(url_for('add_kedi'))
            
            # Create new KEDI record
            record = RasanRecord(
                date=date,
                kedi_m=int(request.form['kedi_m']),  # Male prisoners in KEDI
                kedi_f=int(request.form['kedi_f']),  # Female prisoners in KEDI
                tifin_m=int(request.form['tifin_m']),  # Male prisoners in Tifin
                tifin_f=int(request.form['tifin_f']),  # Female prisoners in Tifin
                medical_m=int(request.form['medical_m']),  # Male prisoners in medical
                medical_f=int(request.form['medical_f'])  # Female prisoners in medical
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
    # Get record by ID or return 404 if not found
    record = RasanRecord.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Update record fields
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
    # Delete record by ID
    record = RasanRecord.query.get_or_404(id)
    db.session.delete(record)
    db.session.commit()
    flash('Record deleted successfully!', 'success')
    return redirect(url_for('kedi'))

# Routes for Stock Items management
@app.route('/stock_items')
def stock_items():
    # List all stock items ordered by name
    items = StockItem.query.order_by(StockItem.item_name).all()
    return render_template('stock_items/list.html', items=items)

@app.route('/stock_items/add', methods=['GET', 'POST'])
def add_stock_item():
    if request.method == 'POST':
        try:
            # Create new stock item
            item = StockItem(
                item_name=request.form['item_name'],  # Item name
                description=request.form.get('description', ''),  # Optional description
                unit=request.form['unit']  # Measurement unit (kg, liter, etc.)
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
    # Get stock item by ID
    item = StockItem.query.get_or_404(id)
    if request.method == 'POST':
        try:
            # Update item fields
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
    # Delete stock item by ID
    item = StockItem.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Stock item deleted successfully!', 'success')
    return redirect(url_for('stock_items'))

# Routes for Stock Inventory management
@app.route('/stock_inventory')
def stock_inventory():
    # List inventory with pagination and filtering options
    page = request.args.get('page', 1, type=int)
    item_id = request.args.get('item_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = StockInventory.query.order_by(StockInventory.date.desc())
    
    # Apply filters if provided
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
    # Get all stock items for dropdown
    stock_items = StockItem.query.order_by(StockItem.item_name).all()
    
    if request.method == 'POST':
        try:
            # Create new inventory entry
            entry = StockInventory(
                stock_item_id=int(request.form['stock_item']),  # Reference to stock item
                quantity=float(request.form['quantity']),  # Quantity added/removed
                date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),  # Transaction date
                notes=request.form.get('notes', '')  # Optional notes
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
    # Get inventory entry by ID
    entry = StockInventory.query.get_or_404(id)
    stock_items = StockItem.query.order_by(StockItem.item_name).all()
    
    if request.method == 'POST':
        try:
            # Update entry fields
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
    # Delete inventory entry by ID
    entry = StockInventory.query.get_or_404(id)
    db.session.delete(entry)
    db.session.commit()
    flash('Stock entry deleted successfully!', 'success')
    return redirect(url_for('stock_inventory'))

@app.route('/stock_inventory/item/<int:item_id>')
def stock_inventory_by_item(item_id):
    # Show inventory entries for a specific item
    item = StockItem.query.get_or_404(item_id)
    inventory = StockInventory.query.filter_by(stock_item_id=item_id)\
                   .order_by(StockInventory.date.desc())\
                   .all()
    return render_template('stock_inventory/list_by_item.html', 
                         inventory=inventory, 
                         item=item)

# Routes for Scale management (daily ration scales)
@app.route('/scale')
def scale_list():
    # List all scale entries
    entries = ScaleEntry.query.all()
    return render_template('scale/scale_list.html', entries=entries)

@app.route('/scale/add', methods=['GET', 'POST'])
def add_scale():
    # Get all stock items for dropdown
    stock_items = StockItem.query.all()
    
    if request.method == 'POST':
        try:
            stock_item_id = int(request.form['stock_item'])
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
            
            # Check for overlapping date ranges for the same item
            overlap = ScaleEntry.query.filter(
                ScaleEntry.stock_item_id == stock_item_id,
                ScaleEntry.start_date <= end_date,
                ScaleEntry.end_date >= start_date
            ).first()
            
            if overlap:
                flash('This item already has a scale entry for the selected date range!', 'danger')
                return redirect(url_for('add_scale'))
            
            # Create new scale entry with daily ration values
            entry = ScaleEntry(
                stock_item_id=stock_item_id,
                start_date=start_date,
                end_date=end_date,
                monday=float(request.form['monday']),    # Monday ration
                tuesday=float(request.form['tuesday']),   # Tuesday ration
                wednesday=float(request.form['wednesday']), # Wednesday ration
                thursday=float(request.form['thursday']),  # Thursday ration
                friday=float(request.form['friday']),      # Friday ration
                saturday=float(request.form['saturday']),  # Saturday ration
                sunday=float(request.form['sunday'])       # Sunday ration
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
    # Get scale entry by ID
    entry = ScaleEntry.query.get_or_404(id)
    stock_items = StockItem.query.all()
    
    if request.method == 'POST':
        try:
            # Check for overlapping date ranges (excluding current entry)
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
            
            # Update scale entry fields
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
    # Delete scale entry by ID
    entry = ScaleEntry.query.get_or_404(id)
    db.session.delete(entry)
    db.session.commit()
    flash('Scale entry deleted successfully!', 'success')
    return redirect(url_for('scale_list'))
# Add new routes after existing ones
@app.route('/daily_stock_movement', methods=['GET', 'POST'])
def daily_stock_movement():
    if request.method == 'POST':
        try:
            # Get form inputs
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
            item_id = int(request.form['item_id'])
            
            # Get the selected item
            item = StockItem.query.get_or_404(item_id)
            
            # Initialize results dictionary
            results = []
            
            # Get scale entries that cover our date range - properly ordered
            scale_entries = ScaleEntry.query.filter(
                ScaleEntry.stock_item_id == item_id,
                ScaleEntry.start_date <= end_date,
                ScaleEntry.end_date >= start_date
            ).order_by(ScaleEntry.start_date).all()
            
            # Get all inventory transactions for the item - properly ordered
            inventory_transactions = StockInventory.query.filter(
                StockInventory.stock_item_id == item_id,
                StockInventory.date.between(start_date, end_date)
            ).order_by(StockInventory.date).all()
            
            # Get all prisoner records for the date range - properly ordered
            prisoner_records = RasanRecord.query.filter(
                RasanRecord.date.between(start_date, end_date)
            ).order_by(RasanRecord.date).all()
            
            # Create a date range
            date_range = []
            current_date = start_date
            while current_date <= end_date:
                date_range.append(current_date)
                current_date += timedelta(days=1)
            
            # Calculate opening balance from transactions before start date
            opening_balance_query = db.session.query(
                func.sum(StockInventory.quantity).label('total')
            ).filter(
                StockInventory.stock_item_id == item_id,
                StockInventory.date < start_date
            )
            
            opening_balance_result = opening_balance_query.first()
            opening_balance = opening_balance_result[0] if opening_balance_result[0] else 0.0
            
            for day_date in date_range:
                # Initialize daily record
                day_record = {
                    'date': day_date,
                    'day_name': day_date.strftime('%A'),
                    'opening_balance': opening_balance,
                    'incoming_stock': 0.0,
                    'total_stock': opening_balance,
                    'kedi_total': 0,
                    'scale_value': 0.0,
                    'consumption': 0.0,
                    'closing_balance': opening_balance
                }
                
                # Add incoming stock for this date
                for transaction in inventory_transactions:
                    if transaction.date == day_date:
                        day_record['incoming_stock'] += transaction.quantity
                
                # Calculate total available stock
                day_record['total_stock'] = day_record['opening_balance'] + day_record['incoming_stock']
                
                # Get prisoner count for this date
                prisoner_record = next((r for r in prisoner_records if r.date == day_date), None)
                if prisoner_record:
                    # Calculate total prisoners (KEDI - (Tifin + Medical))
                    day_record['kedi_total'] = (prisoner_record.kedi_m + prisoner_record.kedi_f) - \
                                             (prisoner_record.tifin_m + prisoner_record.tifin_f + 
                                              prisoner_record.medical_m + prisoner_record.medical_f)
                
                # Get scale value for this day of week
                for scale in scale_entries:
                    if scale.start_date <= day_date <= scale.end_date:
                        day_record['scale_value'] = getattr(scale, day_record['day_name'].lower(), 0.0)
                        break
                
                # Calculate consumption
                day_record['consumption'] = day_record['kedi_total'] * day_record['scale_value']
                
                # Calculate closing balance
                day_record['closing_balance'] = day_record['total_stock'] - day_record['consumption']
                
                # Add to results
                results.append(day_record)
                
                # Set opening balance for next day
                opening_balance = day_record['closing_balance']
            
            # Get all items for dropdown
            all_items = StockItem.query.order_by(StockItem.item_name).all()
            
            return render_template('daily_stock_movement/report.html',
                               results=results,
                               all_items=all_items,
                               selected_item=item,
                               start_date=start_date.strftime('%Y-%m-%d'),
                               end_date=end_date.strftime('%Y-%m-%d'))
            
        except Exception as e:
            flash(f'Error generating report: {str(e)}', 'danger')
            return redirect(url_for('daily_stock_movement'))
    
    # GET request - show empty form
    all_items = StockItem.query.order_by(StockItem.item_name).all()
    return render_template('daily_stock_movement/report.html',
                         all_items=all_items)
@app.route('/export_daily_stock_movement', methods=['POST'])
def export_daily_stock_movement():
    try:
        # Get form inputs
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        item_id = int(request.form['item_id'])
        
        # Get the selected item
        item = StockItem.query.get_or_404(item_id)
        
        # Get all required data
        scale_entries = ScaleEntry.query.filter(
            ScaleEntry.stock_item_id == item_id,
            ScaleEntry.start_date <= end_date,
            ScaleEntry.end_date >= start_date
        ).order_by(ScaleEntry.start_date).all()

        inventory_transactions = StockInventory.query.filter(
            StockInventory.stock_item_id == item_id,
            StockInventory.date.between(start_date, end_date)
        ).order_by(StockInventory.date).all()

        prisoner_records = RasanRecord.query.filter(
            RasanRecord.date.between(start_date, end_date)
        ).order_by(RasanRecord.date).all()

        # Calculate opening balance
        opening_balance = db.session.query(
            func.sum(StockInventory.quantity).label('total')
        ).filter(
            StockInventory.stock_item_id == item_id,
            StockInventory.date < start_date
        ).scalar() or 0.0

        # Process daily records
        records = []
        current_date = start_date
        while current_date <= end_date:
            day_record = {
                'date': current_date,
                'day_name': current_date.strftime('%A'),
                'opening_balance': float(opening_balance),
                'incoming_stock': 0.0,
                'total_stock': float(opening_balance),
                'kedi_total': 0,
                'scale_value': 0.0,
                'consumption': 0.0,
                'closing_balance': float(opening_balance)
            }

            # Calculate incoming stock
            for transaction in inventory_transactions:
                if transaction.date == current_date:
                    day_record['incoming_stock'] += float(transaction.quantity)

            day_record['total_stock'] = day_record['opening_balance'] + day_record['incoming_stock']

            # Calculate prisoner count
            prisoner_record = next((r for r in prisoner_records if r.date == current_date), None)
            if prisoner_record:
                day_record['kedi_total'] = (prisoner_record.kedi_m + prisoner_record.kedi_f) - \
                                         (prisoner_record.tifin_m + prisoner_record.tifin_f + 
                                          prisoner_record.medical_m + prisoner_record.medical_f)

            # Get scale value
            for scale in scale_entries:
                if scale.start_date <= current_date <= scale.end_date:
                    day_record['scale_value'] = float(getattr(scale, day_record['day_name'].lower(), 0.0))
                    break

            day_record['consumption'] = day_record['kedi_total'] * day_record['scale_value']
            day_record['closing_balance'] = day_record['total_stock'] - day_record['consumption']

            records.append(day_record)
            opening_balance = day_record['closing_balance']
            current_date += timedelta(days=1)

        # Create DataFrame
        df = pd.DataFrame.from_records(records)
        
        # Add totals row (excluding date and day_name columns)
        totals = pd.DataFrame({
            'date': ['Total'],
            'day_name': [''],
            'opening_balance': [df['opening_balance'].iloc[0]],  # First day's opening
            'incoming_stock': [df['incoming_stock'].sum()],
            'total_stock': [''],
            'kedi_total': [df['kedi_total'].sum()],
            'scale_value': [''],
            'consumption': [df['consumption'].sum()],
            'closing_balance': [df['closing_balance'].iloc[-1]]  # Last day's closing
        })
        df = pd.concat([df, totals], ignore_index=True)

        # Format and rename columns
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        column_mapping = {
            'date': 'Date',
            'day_name': 'Day',
            'opening_balance': 'Opening Balance',
            'incoming_stock': 'Incoming Stock',
            'total_stock': 'Total Stock',
            'kedi_total': 'Prisoners Count',
            'scale_value': 'Scale Value',
            'consumption': 'Daily Consumption',
            'closing_balance': 'Closing Balance'
        }
        df = df.rename(columns=column_mapping)

    except Exception as e:
        flash(f'Error exporting report: {str(e)}', 'danger')
        return redirect(url_for('daily_stock_movement'))



@app.route('/export_daily_stock/excel', methods=['POST'])
def export_daily_stock_excel():
    try:
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        item_id = int(request.form['item_id'])
        
        exporter = ReportExporter(item_id, start_date, end_date)
        excel_file = exporter.export_excel()
        
        filename = f"daily_stock_{exporter.item.item_name}_{start_date}_{end_date}.xlsx"
        return send_file(
            excel_file,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        flash(f'Error exporting Excel: {str(e)}', 'danger')
        return redirect(url_for('daily_stock_movement'))

@app.route('/export_daily_stock/pdf', methods=['POST'])
def export_daily_stock_pdf():
    try:
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        item_id = int(request.form['item_id'])
        
        exporter = ReportExporter(item_id, start_date, end_date)
        pdf_file = exporter.export_pdf()
        
        filename = f"daily_stock_{exporter.item.item_name}_{start_date}_{end_date}.pdf"
        return send_file(
            pdf_file,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        flash(f'Error exporting PDF: {str(e)}', 'danger')
        return redirect(url_for('daily_stock_movement'))
# Main entry point
if __name__ == '__main__':
    app.run(debug=True)