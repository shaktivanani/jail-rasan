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