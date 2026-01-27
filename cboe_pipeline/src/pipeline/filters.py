import pandas as pd
from typing import List, Dict, Any
from .config import Config

class Filters:
    def __init__(self, config: Config):
        self.universe = set(config.underlyings)
        self.filters_cfg = config.filters

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
            
        initial_count = len(df)
        
        # 1. Universe filter
        # Ensure 'root_symbol' is in universe
        df = df[df['root_symbol'].isin(self.universe)]
        
        # 2. Validity checks
        if self.filters_cfg.get("require_volume_geq_0", True):
            df = df[df['volume'] >= 0]
            
        if self.filters_cfg.get("drop_zero_volume", False):
            df = df[df['volume'] > 0]
            
        return df
