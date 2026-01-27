import requests
from bs4 import BeautifulSoup

def run():
    url = "https://www.cboe.com/us/options/market_statistics/daily/"
    r = requests.get(url)
    with open("analysis/daily_page.html", "w") as f:
        f.write(r.text)
        
    soup = BeautifulSoup(r.text, 'html.parser')
    print("--- LINKS on Daily Page ---")
    for a in soup.find_all('a'):
        href = a.get('href', '')
        text = a.get_text(strip=True)
        if 'zip' in href or 'csv' in href or 'download' in text.lower():
            print(f"Link: {text[:50]}... href={href}")

if __name__ == "__main__":
    run()
