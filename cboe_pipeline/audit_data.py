import pandas as pd
import pyarrow.parquet as pq
import os
from glob import glob
from datetime import datetime

def audit():
    base_dir = "data/parquet"
    if not os.path.exists(base_dir):
        print("No parquet data found.")
        return

    print("Scanning dataset...")
    
    # We can scan by partition or use pyarrow dataset
    import pyarrow.dataset as ds
    dataset = ds.dataset(base_dir, partitioning="hive")
    
    # Files
    files = dataset.files
    print(f"Total Parquet Files: {len(files)}")
    
    # Get all root symbols
    # glob is safer for partition discovery than scanning full dataset if huge overhead
    root_symbols = [d.split('=')[-1] for d in glob(f"{base_dir}/root_symbol=*")]
    print(f"Unique Tickers: {len(root_symbols)}")
    print(f"Tickers: {sorted(root_symbols)}")
    
    # Inspect ranges significantly (e.g. min/max date) by checking a few files or using dataset fragment scan?
    # Scanning entire 10yr dataset might be slow. 
    # Let's check min/max year partitions first.
    
    years = sorted([int(d.split('=')[-1]) for d in glob(f"{base_dir}/root_symbol=*/year=*")])
    if years:
        print(f"Year Range: {min(years)} to {max(years)}")
    
    # Sample Row Count Estimate?
    # Or just count rows. 5800 files.
    # Let's count quickly.
    
    total_rows = 0
    # Scanner is fastest
    # Count rows using dataset scanner
    scanner = dataset.scanner(columns=["volume"])
    total_rows = scanner.count_rows()
    print(f"Total Rows: {total_rows:,}")
    
    print("\n--- Example Data (Top 5 Rows) ---")
    print(scanner.head(5).to_pandas())

if __name__ == "__main__":
    audit()
