import io
from datetime import datetime, timedelta
import pandas as pd
from flask import send_file
from fpdf import FPDF
from models import db, StockItem, StockInventory, ScaleEntry, RasanRecord
from sqlalchemy import func

class ReportExporter:
    def __init__(self, item_id, start_date, end_date):
        self.item_id = item_id
        self.start_date = start_date
        self.end_date = end_date
        self.item = StockItem.query.get_or_404(item_id)
        self.scale_entries = self._get_scale_entries()
        self.inventory_transactions = self._get_inventory_transactions()
        self.prisoner_records = self._get_prisoner_records()
        self.opening_balance = self._calculate_opening_balance()
        self.records = self._generate_records()

    def _get_scale_entries(self):
        return ScaleEntry.query.filter(
            ScaleEntry.stock_item_id == self.item_id,
            ScaleEntry.start_date <= self.end_date,
            ScaleEntry.end_date >= self.start_date
        ).order_by(ScaleEntry.start_date).all()

    def _get_inventory_transactions(self):
        return StockInventory.query.filter(
            StockInventory.stock_item_id == self.item_id,
            StockInventory.date.between(self.start_date, self.end_date)
        ).order_by(StockInventory.date).all()

    def _get_prisoner_records(self):
        return RasanRecord.query.filter(
            RasanRecord.date.between(self.start_date, self.end_date)
        ).order_by(RasanRecord.date).all()

    def _calculate_opening_balance(self):
        return db.session.query(
            func.sum(StockInventory.quantity).label('total')
        ).filter(
            StockInventory.stock_item_id == self.item_id,
            StockInventory.date < self.start_date
        ).scalar() or 0.0

    def _generate_records(self):
        records = []
        current_date = self.start_date
        opening_balance = float(self.opening_balance)
        
        while current_date <= self.end_date:
            day_record = self._create_day_record(current_date, opening_balance)
            records.append(day_record)
            opening_balance = day_record['closing_balance']
            current_date += timedelta(days=1)
        
        return records

    def _create_day_record(self, current_date, opening_balance):
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
        for transaction in self.inventory_transactions:
            if transaction.date == current_date:
                day_record['incoming_stock'] += float(transaction.quantity)

        day_record['total_stock'] = day_record['opening_balance'] + day_record['incoming_stock']

        # Calculate prisoner count
        prisoner_record = next((r for r in self.prisoner_records if r.date == current_date), None)
        if prisoner_record:
            day_record['kedi_total'] = (prisoner_record.kedi_m + prisoner_record.kedi_f) - \
                                     (prisoner_record.tifin_m + prisoner_record.tifin_f + 
                                      prisoner_record.medical_m + prisoner_record.medical_f)

        # Get scale value
        for scale in self.scale_entries:
            if scale.start_date <= current_date <= scale.end_date:
                day_record['scale_value'] = float(getattr(scale, day_record['day_name'].lower(), 0.0))
                break

        day_record['consumption'] = day_record['kedi_total'] * day_record['scale_value']
        day_record['closing_balance'] = day_record['total_stock'] - day_record['consumption']

        return day_record

    def export_excel(self):
        try:
            # Create DataFrame
            df = pd.DataFrame.from_records(self.records)
            
            # Add totals row
            totals = self._create_totals_row(df)
            df = pd.concat([df, totals], ignore_index=True)

            # Format and rename columns
            df = self._format_dataframe(df)

            # Create Excel file
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Daily Stock', index=False)
                self._format_excel(writer, df)
            
            output.seek(0)
            return output
        
        except Exception as e:
            raise Exception(f"Excel export error: {str(e)}")

    def export_pdf(self):
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            # Add title
            self._add_pdf_header(pdf)
            
            # Create table
            self._add_pdf_table(pdf)
            
            # Add summary
            self._add_pdf_summary(pdf)
            
            # Save to buffer
            output = io.BytesIO()
            pdf.output(output)
            output.seek(0)
            return output
        
        except Exception as e:
            raise Exception(f"PDF export error: {str(e)}")

    def _create_totals_row(self, df):
        return pd.DataFrame({
            'date': ['Total'],
            'day_name': [''],
            'opening_balance': [df['opening_balance'].iloc[0]],
            'incoming_stock': [df['incoming_stock'].sum()],
            'total_stock': [''],
            'kedi_total': [df['kedi_total'].sum()],
            'scale_value': [''],
            'consumption': [df['consumption'].sum()],
            'closing_balance': [df['closing_balance'].iloc[-1]]
        })

    def _format_dataframe(self, df):
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        column_mapping = {
            'date': 'Date',
            'day_name': 'Day',
            'opening_balance': 'Opening',
            'incoming_stock': 'Incoming',
            'total_stock': 'Total Stock',
            'kedi_total': 'Prisoners',
            'scale_value': 'Scale',
            'consumption': 'Used',
            'closing_balance': 'Closing'
        }
        return df.rename(columns=column_mapping)

    def _format_excel(self, writer, df):
        workbook = writer.book
        worksheet = writer.sheets['Daily Stock']
        
        # Header formatting
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#4472C4', 'font_color': 'white', 'border': 1
        })
        
        # Number formatting
        num_format = workbook.add_format({'num_format': '0.00'})
        int_format = workbook.add_format({'num_format': '0'})
        
        # Apply formatting
        for col_num, col_name in enumerate(df.columns):
            worksheet.write(0, col_num, col_name, header_format)
            
            if col_name in ['Opening', 'Incoming', 'Total Stock', 'Scale', 'Used', 'Closing']:
                worksheet.set_column(col_num, col_num, 12, num_format)
            elif col_name == 'Prisoners':
                worksheet.set_column(col_num, col_num, 12, int_format)
            else:
                worksheet.set_column(col_num, col_num, 12)
        
        # Total row formatting
        total_format = workbook.add_format({
            'bold': True, 'top': 2, 'num_format': '0.00'
        })
        
        last_row = len(df)
        for col_num, col_name in enumerate(df.columns):
            if col_name in ['Opening', 'Incoming', 'Used', 'Closing']:
                worksheet.write(last_row, col_num, df[col_name].iloc[-1], total_format)
        
        # Add title and metadata
        title_format = workbook.add_format({
            'bold': True, 'size': 16, 'align': 'center'
        })
        
        worksheet.merge_range('A1:I1', f'Daily Stock - {self.item.item_name}', title_format)
        worksheet.write('A2', f'Period: {self.start_date} to {self.end_date}')
        worksheet.write('A3', f'Unit: {self.item.unit}')

    def _add_pdf_header(self, pdf):
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, f'Daily Stock Movement - {self.item.item_name}', 0, 1, 'C')
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 8, f'Period: {self.start_date} to {self.end_date}', 0, 1, 'C')
        pdf.cell(0, 8, f'Unit: {self.item.unit}', 0, 1, 'C')
        pdf.ln(5)

    def _add_pdf_table(self, pdf):
        # Table header
        pdf.set_font('Arial', 'B', 10)
        col_widths = [22, 15, 15, 15, 20, 15, 15, 15, 15]
        headers = ['Date', 'Day', 'Opening', 'Incoming', 'Total Stock', 
                 'Prisoners', 'Scale', 'Used', 'Closing']
        
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 10, header, 1, 0, 'C')
        pdf.ln()
        
        # Table rows
        pdf.set_font('Arial', '', 10)
        for record in self.records:
            self._add_pdf_table_row(pdf, record, col_widths)
        
        # Totals row
        pdf.set_font('Arial', 'B', 10)
        totals = self._calculate_pdf_totals()
        self._add_pdf_table_row(pdf, totals, col_widths, is_total=True)

    def _add_pdf_table_row(self, pdf, record, col_widths, is_total=False):
        if is_total:
            pdf.set_fill_color(230, 230, 230)
        else:
            pdf.set_fill_color(255, 255, 255)
        
        cells = [
            record['date'].strftime('%Y-%m-%d') if not is_total else 'TOTAL',
            record['day_name'] if not is_total else '',
            f"{record['opening_balance']:.2f}",
            f"{record['incoming_stock']:.2f}" if not is_total else f"{sum(r['incoming_stock'] for r in self.records):.2f}",
            f"{record['total_stock']:.2f}" if not is_total else '',
            str(record['kedi_total']) if not is_total else str(sum(r['kedi_total'] for r in self.records)),
            f"{record['scale_value']:.3f}" if not is_total else '',
            f"{record['consumption']:.2f}" if not is_total else f"{sum(r['consumption'] for r in self.records):.2f}",
            f"{record['closing_balance']:.2f}" if not is_total else f"{self.records[-1]['closing_balance']:.2f}"
        ]
        
        for i, cell in enumerate(cells):
            pdf.cell(col_widths[i], 10, cell, 1, 0, 'C', True)
        pdf.ln()

    def _calculate_pdf_totals(self):
        return {
            'opening_balance': self.records[0]['opening_balance'],
            'incoming_stock': sum(r['incoming_stock'] for r in self.records),
            'kedi_total': sum(r['kedi_total'] for r in self.records),
            'consumption': sum(r['consumption'] for r in self.records),
            'closing_balance': self.records[-1]['closing_balance']
        }

    def _add_pdf_summary(self, pdf):
        pdf.ln(10)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Summary', 0, 1)
        pdf.set_font('Arial', '', 10)
        
        totals = self._calculate_pdf_totals()
        net_change = totals['incoming_stock'] - totals['consumption']
        
        summary_data = [
            ('Total Incoming Stock:', f"{totals['incoming_stock']:.2f} {self.item.unit}"),
            ('Total Consumption:', f"{totals['consumption']:.2f} {self.item.unit}"),
            ('Net Change:', f"{net_change:.2f} {self.item.unit}")
        ]
        
        for label, value in summary_data:
            pdf.cell(60, 8, label, 0, 0)
            pdf.cell(0, 8, value, 0, 1)