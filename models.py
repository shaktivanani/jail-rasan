from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class RasanRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    kedi_m = db.Column(db.Integer, nullable=False, default=0)
    kedi_f = db.Column(db.Integer, nullable=False, default=0)
    tifin_m = db.Column(db.Integer, nullable=False, default=0)
    tifin_f = db.Column(db.Integer, nullable=False, default=0)
    medical_m = db.Column(db.Integer, nullable=False, default=0)
    medical_f = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return f'<RasanRecord {self.date}>'

    def total(self):
        return (self.kedi_m + self.kedi_f) - (self.tifin_m + self.tifin_f) - (self.medical_m + self.medical_f)
    
    def kedi_total(self):
        return self.kedi_m + self.kedi_f
    
    def tifin_total(self):
        return self.tifin_m + self.tifin_f
    
    def medical_total(self):
        return self.medical_m + self.medical_f
    
class StockItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)  # kg, ml, packets, etc.
    notes = db.Column(db.Text)

    def __repr__(self):
        return f'<StockItem {self.item_name} - {self.quantity}{self.unit}>'

class ScaleEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stock_item_id = db.Column(db.Integer, db.ForeignKey('stock_item.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    monday = db.Column(db.Float, default=0.0)
    tuesday = db.Column(db.Float, default=0.0)
    wednesday = db.Column(db.Float, default=0.0)
    thursday = db.Column(db.Float, default=0.0)
    friday = db.Column(db.Float, default=0.0)
    saturday = db.Column(db.Float, default=0.0) 
    sunday = db.Column(db.Float, default=0.0)
    
    stock_item = db.relationship('StockItem', backref='scale_entries')


    def __repr__(self):
        return f'<ScaleEntry {self.stock_item.item_name} {self.start_date}-{self.end_date}>'