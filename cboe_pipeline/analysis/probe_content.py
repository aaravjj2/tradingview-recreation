import requests

def probe_content():
    base_url = "https://www.cboe.com/us/options/market_statistics/historical_data/download/class/"
    params = {
        "reportType": "volume",
        "volumeType": "sum",
        "volumeAggType": "daily",
        "symbolType": "osiRoot",
        "symbol": "SPY",
        "startDate": "2023-01-23",
        "endDate": "2023-01-23"
    }
    r = requests.get(base_url, params=params, stream=True)
    if r.status_code == 200:
        lines = []
        for line in r.iter_lines():
            if line:
                lines.append(line.decode('utf-8'))
            if len(lines) > 5:
                break
        print("\n".join(lines))
    else:
        print(f"Failed: {r.status_code}")

if __name__ == "__main__":
    probe_content()
