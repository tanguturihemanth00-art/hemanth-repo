from models.excel_record import ExcelRecord

class DemoRecord(ExcelRecord):
    task_id: str
    action: str
