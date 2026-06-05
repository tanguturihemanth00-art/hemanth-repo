"""
services/village_excel_parser.py
================================
Utility to parse Village, Month, and Year out of an Excel sheet name.
"""

from __future__ import annotations

import pandas as pd
from pathlib import Path
from typing import Tuple

from framework.core.logger import get_logger

_log = get_logger()

class VillageExcelParser:
    """Helper to read the sheet name from an Excel file."""

    @classmethod
    def extract_metadata_from_sheet(cls, filepath: str | Path) -> Tuple[str, str, str]:
        """
        Reads the first sheet name in the Excel file and attempts to parse it.
        Expected Format: VillageName_Month_Year (e.g. Springfield_August_2023)
        
        Returns:
            A tuple of (village_name, month, year).
            If it fails to parse, returns ("UnknownVillage", "UnknownMonth", "UnknownYear")
        """
        path = Path(filepath)
        if not path.exists():
            _log.error("Input file does not exist: {path}", path=path)
            return "UnknownVillage", "UnknownMonth", "UnknownYear"

        try:
            excel_file = pd.ExcelFile(path)
            sheet_names = excel_file.sheet_names
            
            if not sheet_names:
                _log.error("Excel file has no sheets.")
                return "UnknownVillage", "UnknownMonth", "UnknownYear"
                
            first_sheet = sheet_names[0]
            _log.info(f"Parsing metadata from sheet name: '{first_sheet}'")
            
            # Expecting format: VillageName_Month_Year
            parts = first_sheet.split("_")
            
            if len(parts) >= 3:
                # If village name has underscores, join everything but last two parts
                village_name = "_".join(parts[:-2])
                month = parts[-2]
                year = parts[-1]
                return village_name, month, year
            else:
                _log.warning(f"Sheet name '{first_sheet}' doesn't match format 'Village_Month_Year'.")
                return first_sheet, "UnknownMonth", "UnknownYear"
                
        except Exception as exc:
            _log.error(f"Failed to parse Excel sheet name: {exc}")
            return "UnknownVillage", "UnknownMonth", "UnknownYear"
