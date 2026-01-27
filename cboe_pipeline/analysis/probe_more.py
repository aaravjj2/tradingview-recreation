import requests

def probe_variants():
    base_url = "https://www.cboe.com/us/options/market_statistics/historical_data/download/class/"
    variants = [
        "detail", "summary", "price", "quote", "raw", "full", "chain", "symbol",
        "market_stats", "daily_stats", "month", "monthly"
    ]
    
    for v in variants:
        params = {
            "reportType": v,
            "volumeType": "sum",
            "volumeAggType": "daily",
            "symbolType": "osiRoot",
            "symbol": "SPY",
            "startDate": "2023-01-23",
            "endDate": "2023-01-23"
        }
        try:
            r = requests.get(base_url, params=params, stream=True)
            if r.status_code == 200:
                print(f"Found Type: {v}")
                print(r.headers.get("Content-Type"))
            elif r.status_code != 404:
                print(f"Type {v}: {r.status_code}")
        except:
            pass

def probe_daily_url():
    url = "https://www.cboe.com/us/options/market_statistics/daily/"
    try:
        r = requests.get(url)
        print(f"Daily URL Status: {r.status_code}")
        if "Download" in r.text or ".csv" in r.text or ".zip" in r.text:
            print("Daily page contains download links.")
        else:
            print("Daily page does not obviously contain download links.")
    except Exception as e:
        print(f"Daily probe failed: {e}")

if __name__ == "__main__":
    print("--- Probe Variants ---")
    probe_variants()
    print("\n--- Probe Daily ---")
    probe_daily_url()
