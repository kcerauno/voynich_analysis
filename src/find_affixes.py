import sqlite3
import re
from collections import Counter
import sys

def main():
    db_path = r'data\voynich.db'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT word FROM words WHERE word IS NOT NULL AND word != '';")
    words = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    print(f"Total entries fetched: {len(words)}")
    
    # Clean the words: keep only alphabetical characters (assuming EVA transliteration)
    cleaned_words = [re.sub(r'[^a-zA-Z]', '', w) for w in words]
    cleaned_words = [w for w in cleaned_words if len(w) > 0]
    
    total_valid = len(cleaned_words)
    print(f"Total valid words after cleaning: {total_valid}")
    
    # Analyze prefixes and suffixes of length 1 to 4
    for n in range(1, 5):
        prefixes = Counter()
        suffixes = Counter()
        
        for w in cleaned_words:
            if len(w) > n:  # Consider as affix only if the word is longer than the affix itself
                prefixes[w[:n]] += 1
                suffixes[w[-n:]] += 1
                
        print(f"\n=========================================")
        print(f" Length {n} Affixes")
        print(f"=========================================")
        
        print(f"\n--- Top 20 Prefixes (Length {n}) ---")
        for fix, count in prefixes.most_common(20):
            percentage = (count / total_valid) * 100
            print(f"{fix:<6}: {count:>6}  ({percentage:>5.2f}%)")
            
        print(f"\n--- Top 20 Suffixes (Length {n}) ---")
        for fix, count in suffixes.most_common(20):
            percentage = (count / total_valid) * 100
            print(f"{fix:<6}: {count:>6}  ({percentage:>5.2f}%)")

if __name__ == "__main__":
    with open(r'affix_analysis.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        main()
