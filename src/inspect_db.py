import sqlite3
import os

db_path = r'data\voynich.db'

def get_db_info():
    if not os.path.exists(db_path):
        print(f"Error: {db_path} does not exist.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]

    with open('db_layout.txt', 'w', encoding='utf-8') as f:
        f.write(f"Tables found: {tables}\n")

        for table in tables:
            f.write(f"\n--- Layout for table: {table} ---\n")
            cursor.execute(f"PRAGMA table_info('{table}');")
            columns = cursor.fetchall()
            f.write(f"{'ID':<4} {'Name':<20} {'Type':<10} {'NotNull':<8} {'PK':<3}\n")
            f.write("-" * 50 + "\n")
            for col in columns:
                # col: (id, name, type, notnull, default_value, pk)
                f.write(f"{col[0]:<4} {col[1]:<20} {col[2]:<10} {col[3]:<8} {col[5]:<3}\n")

    conn.close()

if __name__ == "__main__":
    get_db_info()
