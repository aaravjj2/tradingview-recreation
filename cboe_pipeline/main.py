import argparse
import logging
import sys
import os
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.pipeline.config import Config
from src.pipeline.datastore import DataStore
from src.pipeline.downloader import CboeAggregateVolumeSource
from src.pipeline.parser import Parser
from src.pipeline.filters import Filters
from src.pipeline.writer import Writer
from src.pipeline.verify import Verifier

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_task(config, db, source, month_str, symbol):
    """
    Executes the pipeline for a single (month, symbol) task.
    """
    try:
        y, m = map(int, month_str.split('-'))
        
        # 1. Check DB state
        task = db.get_task(month_str, symbol)
        if task and task['status'] == 'PROCESSED':
            logger.info(f"Skipping {symbol} {month_str} (already processed)")
            return True

        # 2. Download
        db.update_task(month_str, symbol, "DOWNLOADING")
        output_dir = config.storage['raw_dir']
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            raw_path = source.download_month(symbol, y, m, output_dir)
            db.update_task(month_str, symbol, "DOWNLOADED", file_path=raw_path)
        except Exception as e:
            logger.error(f"Download failed for {symbol} {month_str}: {e}")
            db.update_task(month_str, symbol, "FAILED", last_error=str(e))
            return False

        # 3. Process
        parser = Parser(source.get_schema())
        # Re-load datastore to ensure path correctness or use return value
        # raw_path from download is reliable
        
        try:
            df = parser.parse_file(raw_path, month_str, "run_v1", canonical_symbol=symbol)
            
            filters = Filters(config)
            df = filters.apply(df)
            
            writer = Writer(config.storage['parquet_dir'])
            writer.write(df)
            
            db.update_task(month_str, symbol, "PROCESSED")
            
            if not config.storage.get("keep_raw", False):
                os.remove(raw_path)
                
            return True
            
        except Exception as e:
            logger.error(f"Processing failed for {symbol} {month_str}: {e}")
            db.update_task(month_str, symbol, "FAILED", last_error=str(e))
            return False
            
    except Exception as e:
        logger.critical(f"Critical error in task {symbol} {month_str}: {e}")
        return False

def run_all(config_path: str, dry_run: bool = False):
    config = Config(config_path)
    db = DataStore(config.storage['db_path'])
    source = CboeAggregateVolumeSource(config)
    
    start = pd.Timestamp(config.start_month)
    end = pd.Timestamp(config.end_month)
    months = pd.date_range(start, end, freq='MS').strftime("%Y-%m").tolist()
    
    tasks = []
    for m in months:
        for sym in config.underlyings:
            tasks.append((m, sym))
            
    if dry_run:
        logger.info("Dry run: processing first task only")
        tasks = tasks[:1]
        
    logger.info(f"Generated {len(tasks)} tasks.")
    
    # Process in parallel?
    max_workers = config.download.get("max_workers", 1)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_task, config, db, source, m, s): (m, s) for m, s in tasks}
        
        for future in as_completed(futures):
            m, s = futures[future]
            try:
                res = future.result()
                if res:
                    logger.info(f"Task {s} {m} completed.")
                else:
                    logger.warning(f"Task {s} {m} failed.")
            except Exception as e:
                logger.error(f"Task {s} {m} raised exception: {e}")

def verify(config_path: str):
    config = Config(config_path)
    verifier = Verifier(config)
    errors = verifier.verify_range(config.start_month, config.end_month)
    
    if errors:
        logger.error(f"Verification FAILED with {len(errors)} errors:")
        for e in errors[:10]:
            logger.error(f"  - {e}")
        if len(errors) > 10:
            logger.error("  ... and more.")
        sys.exit(1)
    else:
        logger.info("Verification PASSED.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["run_all", "verify"])
    parser.add_argument("--config", required=True)
    parser.add_argument("--dry-run", action="store_true")
    
    args = parser.parse_args()
    
    if args.command == "run_all":
        run_all(args.config, args.dry_run)
    elif args.command == "verify":
        verify(args.config)

if __name__ == "__main__":
    main()
