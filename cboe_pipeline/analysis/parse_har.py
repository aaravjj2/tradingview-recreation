import json
from urllib.parse import urlparse

def run():
    with open("analysis/cboe_download.har", "r") as f:
        har = json.load(f)
    
    urls = set()
    for entry in har['log']['entries']:
        url = entry['request']['url']
        parsed = urlparse(url)
        if "cboe.com" in parsed.netloc:
            urls.add(url)
            
    print("--- CBOE URLs ---")
    for u in sorted(urls):
        print(u)

if __name__ == "__main__":
    run()
