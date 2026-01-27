import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd
import os
from datetime import datetime

class Writer:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def write(self, df: pd.DataFrame):
        if df.empty:
            return

        # Ensure sorted for deterministic output
        sort_cols = ['trade_date', 'root_symbol', 'exchange', 'product_type'] 
        # Only use existing cols
        available_sort = [c for c in sort_cols if c in df.columns]
        df = df.sort_values(available_sort)

        table = pa.Table.from_pandas(df)
        
        # Partition by root_symbol / year / month
        # We need to extract year/month from trade_date again if strictly following partition
        # But parser added ingest_month. We usually partition by DATA date or INGEST date?
        # Prompt says: "partitioned by: root_symbol / year / month"
        # AND "Deterministic ordering within each partition: sort by trade_date..."
        
        # We will use pyarrow dataset partitioning
        # But simpler: Manual partition write to avoid scattered files
        
        # Group by partition keys
        # Assuming df contains mix of symbols/dates?
        # The pipeline processes (month, symbol) usually. 
        # So df likely contains only 1 symbol / 1 month.
        
        # Let's verify if df has multiple symbols/months.
        # If single, we just write to correct path.
        
        # Safe approach: group by
        
        df['year'] = df['trade_date'].dt.year
        df['month'] = df['trade_date'].dt.month
        
        for keys, group in df.groupby(['root_symbol', 'year', 'month']):
            sym, y, m = keys
            path = os.path.join(self.output_dir, f"root_symbol={sym}", f"year={y}", f"month={m}")
            os.makedirs(path, exist_ok=True)
            
            # File name strategy?
            # if we append, we might duplicate.
            # but we assume atomic overwrite per task?
            # Task is (month, symbol). So we are writing THE file for that task.
            
            fname = f"{sym}_{y}_{m:02d}.parquet"
            out_file = os.path.join(path, fname)
            
            # Write
            group_table = pa.Table.from_pandas(group.drop(columns=['year', 'month']))
            pq.write_table(group_table, out_file, compression='snappy')
