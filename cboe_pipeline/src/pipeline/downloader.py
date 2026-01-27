import os
import requests
import hashlib
import time
import logging
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential
from .interfaces import DataSource

logger = logging.getLogger(__name__)

class CboeAggregateVolumeSource(DataSource):
    def __init__(self, config):
        self.config = config
        self.base_url = "https://www.cboe.com/us/options/market_statistics/historical_data/download/class/"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.download.get("user_agent", "Mozilla/5.0"),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })

    @property
    def name(self) -> str:
        return "cboe_aggregate_volume"

    def _resolve_symbol(self, symbol: str, year: int, month: int) -> str:
        # Simple hardcoded map for now. 
        # Cboe uses historical symbols for historical data.
        # META was FB until June 2022
        if symbol == "META":
            if year < 2022 or (year == 2022 and month < 6):
                return "FB"
        # GOOGL vs GOOG split/rename is complex. 
        # GOOGL (Class A) created April 2014. Before that just GOOG.
        # But Cboe might key everything under GOOG or have both?
        # Let's try GOOG for GOOGL if < 2014 or check specific dates.
        # Ideally we try primary, if empty/fail, try secondary.
        # But this method is called before download.
        if symbol == "GOOGL":
             # GPOGL split occurred April 2014.
             # Before April 2014, map GOOGL to GOOG (pre-split)
             if year < 2014 or (year == 2014 and month < 4):
                 return "GOOG"
        
        # LIN (Linde) merged with Praxair (PX). 
        # New LIN ticker started ~Oct 2018. Prior to that, it was PX (Praxair) on US exchanges.
        if symbol == "LIN":
            if year < 2018 or (year == 2018 and month < 11):
                return "PX"

        return symbol

    def get_schema(self) -> dict:
        return {
            "columns": ["trade_date", "root_symbol", "exchange", "product_type", "volume"],
            "dtypes": {
                "trade_date": "date",
                "root_symbol": "string",
                "exchange": "string",
                "product_type": "string",
                "volume": "int64"
            }
        }

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=60))
    def download_month(self, symbol: str, year: int, month: int, output_dir: str) -> str:
        start_date = f"{year}-{month:02d}-01"
        # End date logic: end of month is tricky without calendar, 
        # but Cboe logic seems to accept a range.
        # Actually, if we want the WHOLE month, we should specify start/end correctly.
        # Let's use a helper to get last day of month.
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        end_date = f"{year}-{month:02d}-{last_day}"

        mapped_symbol = self._resolve_symbol(symbol, year, month)

        params = {
            "reportType": "volume",
            "volumeType": "sum",
            "volumeAggType": "daily",
            "symbolType": "osiRoot",
            "symbol": mapped_symbol,
            "startDate": start_date,
            "endDate": end_date
        }

        # Rate limit
        time.sleep(1.0 / self.config.download.get("rate_limit_rps", 1.0))

        file_name = f"{symbol}_{year}_{month:02d}.csv"
        final_path = os.path.join(output_dir, file_name)
        part_path = final_path + ".part"

        if os.path.exists(final_path):
            # Already exists, check if valid? For now assume yes or rely on verification
            return final_path

        logger.info(f"Downloading {symbol} {year}-{month:02d} to {part_path}")
        
        try:
            with self.session.get(self.base_url, params=params, stream=True, timeout=30) as r:
                r.raise_for_status()
                
                # Check for "no data" responses that are technically 200 OK HTML
                content_type = r.headers.get("Content-Type", "")
                if "text/html" in content_type:
                    # Peek at content to see if it's an error page or empty result
                    # But we are streaming. Let's download first, then inspect.
                    pass

                with open(part_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            
            # Post-download check: Is it HTML error?
            with open(part_path, 'rb') as f:
                head = f.read(1024)
                if b"<!DOCTYPE html>" in head or b"<html" in head:
                     # It's likely an error page or empty result wrapper
                     # Cboe returns 200 OK for some empty searches?
                     # Let's log it.
                     pass
            
            os.rename(part_path, final_path)
            return final_path
            
        except Exception as e:
            if os.path.exists(part_path):
                os.remove(part_path)
            raise e
