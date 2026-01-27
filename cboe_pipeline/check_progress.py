import sqlite3
import time

def check():
    conn = sqlite3.connect("data/pipeline.db")
    cur = conn.cursor()
    cur.execute("select status, count(*) from tasks group by status")
    rows = cur.fetchall()
    print("--- Progress ---")
    total = 0
    for status, count in rows:
        print(f"{status}: {count}")
        total += count
    print(f"Total known tasks: {total}")
    conn.close()

if __name__ == "__main__":
    check()
