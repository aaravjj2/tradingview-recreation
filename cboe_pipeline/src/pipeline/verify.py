import os
import pandas as pd
from typing import List
import logging
from .config import Config

logger = logging.getLogger(__name__)

class Verifier:
    def __init__(self, config: Config):
        self.config = config
        self.parquet_dir = config.storage['parquet_dir']
        self.raw_dir = config.storage['raw_dir']

    def verify_range(self, start_date: str, end_date: str) -> List[str]:
        """
        Verifies completeness and correctness for the given range.
        Returns list of errors (empty list = success).
        """
        errors = []
        
        # generate expected tasks
        # iterate months/symbols
        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)
        
        # Month range
        months = pd.date_range(start, end, freq='MS')
        
        for dt in months:
            y, m = dt.year, dt.month
            for sym in self.config.underlyings:
                # Check Parquet existence
                path = os.path.join(self.parquet_dir, f"root_symbol={sym}", f"year={y}", f"month={m}", f"{sym}_{y}_{m:02d}.parquet")
                
                if not os.path.exists(path):
                    errors.append(f"Missing parquet: {path}")
                    continue
                
                # Load parquet and check basics
                try:
                    df = pd.read_parquet(path)
                    if df.empty:
                        errors.append(f"Empty parquet: {path}")
                    
                    # Volume check
                    if (df['volume'] < 0).any():
                        errors.append(f"Negative volume in {path}")
                        
                    # Schema check
                    required = ['trade_date', 'root_symbol', 'volume']
                    if not all(col in df.columns for col in required):
                        errors.append(f"Schema mismatch in {path}")
                        
                except Exception as e:
                    errors.append(f"Corrupt parquet {path}: {e}")
                    
        return errors
