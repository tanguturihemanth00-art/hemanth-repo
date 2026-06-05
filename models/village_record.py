"""
models/village_record.py
========================
Data model for a village report record.
"""

from typing import Optional
from models.excel_record import ExcelRecord

class VillageRecord(ExcelRecord):
    """
    Model representing a single row in the Village Report excel sheet.
    The actual Village Name, Month, and Year will be injected into this
    model by the workflow after parsing the sheet name.
    """
    
    # We map 'Task ID' or 'ID' to this field based on what's in the Excel.
    # We use Field aliases if needed, but for now we keep it simple.
    # The user said they have many columns but aren't worried right now.
    task_id: Optional[str] = None
    
    # These fields will be populated from the Sheet Name parsing,
    # rather than columns in the excel row itself.
    village_name: Optional[str] = None
    report_month: Optional[str] = None
    report_year: Optional[str] = None
