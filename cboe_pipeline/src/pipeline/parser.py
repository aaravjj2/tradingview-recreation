import pandas as pd
from typing import Dict, Any, List
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class Parser:
    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema
        self.expected_cols = schema["columns"]
        self.dtypes = schema["dtypes"]

    def parse_file(self, file_path: str, ingest_month: str, run_id: str, canonical_symbol: str = None) -> pd.DataFrame:
        """
        Parses a Cboe CSV file, normalizes columns, and enforces schema.
        canonical_symbol: Expected root_symbol (e.g. META). If provided, overrides/maps the file's symbol.
        """
        try:
            # Detect encoding? Cboe usually UTF-8 or ASCII.
            df = pd.read_csv(file_path, on_bad_lines='skip', encoding='utf-8')
            
            # Normalize column names
            df.columns = [c.lower().replace(' ', '_') for c in df.columns]
            
            # Map known columns to canonical
            rename_map = {
                "options_class": "root_symbol",
                "underlying": "reported_symbol" # Sometimes differs?
            }
            df = df.rename(columns=rename_map)
            
            # Ensure trade_date is datetime
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            
            # Add metadata columns
            df['source_file'] = Path(file_path).name
            df['ingest_month'] = ingest_month
            df['run_id'] = run_id
            
            # Handle symbol mapping
            if 'root_symbol' in df.columns:
                 # Backup original symbol to reported_symbol if not present
                 if 'reported_symbol' not in df.columns:
                     df['reported_symbol'] = df['root_symbol']
                 
                 # Force canonical symbol if provided
                 if canonical_symbol:
                     # We can verify overlap or just overwrite. 
                     # Overwriting ensures partitioning works for 'META' even if data says 'FB'
                     df['root_symbol'] = canonical_symbol

            # If 'reported_symbol' missing, use root_symbol
            if 'reported_symbol' not in df.columns and 'root_symbol' in df.columns:
                df['reported_symbol'] = df['root_symbol']
                
            # If 'root_symbol' missing (rare), verify against file name?
            # For now, panic if critical cols missing
            required = ['trade_date', 'root_symbol', 'volume']
            missing = [c for c in required if c not in df.columns]
            if missing:
                raise ValueError(f"Missing required columns in {file_path}: {missing}")
                
            # Enforce dtypes
            for col, dtype in self.dtypes.items():
                if col in df.columns:
                    if dtype == "date":
                        # Keep as timestamp in memory for dt accessors later
                        df[col] = pd.to_datetime(df[col])
                    elif dtype == "int64":
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype('int64')
                    elif dtype == "string":
                        df[col] = df[col].astype(str)
            
            # Reorder / Select canonical columns + extras
            # Keep all columns but put canonical first
            canonical = [c for c in self.expected_cols if c in df.columns]
            others = [c for c in df.columns if c not in canonical]
            
            return df[canonical + others]
            
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            raise e
