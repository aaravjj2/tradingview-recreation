from bs4 import BeautifulSoup
import sys

def run():
    with open("analysis/page.html", "r") as f:
        html = f.read()
    
    soup = BeautifulSoup(html, 'html.parser')
    
    print("--- FORMS ---")
    for form in soup.find_all('form'):
        print(f"Form action: {form.get('action')}")
        for inp in form.find_all('input'):
            print(f"  Input: {inp.get('name')} (type={inp.get('type')})")
    
    print("\n--- BUTTONS ---")
    for btn in soup.find_all('button'):
        text = btn.get_text(strip=True)
        print(f"Button: {text[:50]}... type={btn.get('type')} href={btn.get('href')}")
    
    print("\n--- LINKS with download ---")
    for a in soup.find_all('a'):
        href = a.get('href', '')
        text = a.get_text(strip=True)
        if 'download' in href.lower() or 'download' in text.lower():
            print(f"Link: {text[:50]}... href={href}")

if __name__ == "__main__":
    run()
