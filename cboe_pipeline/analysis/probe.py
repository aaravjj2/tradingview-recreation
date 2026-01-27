import requests

def probe(symbol="SPY", date="2023-01-23"):
    base_url = "https://www.cboe.com/us/options/market_statistics/historical_data/download/class/"
    types = ["volume", "open_interest", "quotedata", "trades", "options", "history", "market"]
    
    for t in types:
        params = {
            "reportType": t,
            "volumeType": "sum", # might be irrelevant for others
            "volumeAggType": "daily",
            "symbolType": "osiRoot",
            "symbol": symbol,
            "startDate": date,
            "endDate": date
        }
        try:
            r = requests.get(base_url, params=params, stream=True)
            print(f"Type: {t}, Status: {r.status_code}, Content-Type: {r.headers.get('Content-Type')}")
            if r.status_code == 200:
                print(f"  Url: {r.url}")
                # peek content
                chunk = next(r.iter_content(1024)).decode('utf-8', errors='ignore')
                print(f"  Content: {chunk[:100]}...")
        except Exception as e:
            print(f"Type {t} failed: {e}")

if __name__ == "__main__":
    probe()
