import sqlite3
import re
from collections import Counter
import sys

PREFIXES = sorted(['qo', 'ch', 'sh', 'ok', 'ot', 'da', 'o', 'c', 'q', 's', 'd'], key=len, reverse=True)
SUFFIXES = sorted(['dy', 'in', 'ey', 'ol', 'ar', 'y', 'n', 'l', 'r'], key=len, reverse=True)

def has_known_affix(word):
    for p in PREFIXES:
        if word.startswith(p):
            return True
    for s in SUFFIXES:
        if word.endswith(s):
            return True
    return False

def main():
    db_path = r'data\voynich.db'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT word FROM words WHERE word IS NOT NULL AND word != '';")
    words = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    cleaned_words = [re.sub(r'[^a-zA-Z]', '', w) for w in words]
    cleaned_words = [w for w in cleaned_words if len(w) >= 3] # Filter out 1-2 letter words
    
    unbound_words = []
    
    for w in cleaned_words:
        if not has_known_affix(w):
            unbound_words.append(w)
            
    # Count occurrences
    unbound_counts = Counter(unbound_words)
    
    print("==================================================")
    print(" Voynich Unbound Roots (V-Words) Analysis ")
    print("==================================================")
    print(f"Total valid words analyzed (length >= 3): {len(cleaned_words)}")
    print(f"Total 'Unbound' words found: {len(unbound_words)}")
    
    if len(cleaned_words) > 0:
        pct = (len(unbound_words) / len(cleaned_words)) * 100
        print(f"Percentage of words that defy standard affix rules: {pct:.2f}%")
        
    print("\n--- Top 20 Most Frequent Unbound Words ---")
    print("These words might be the true 'content' vocabulary (names/nouns) rather than grammatical/cipher constructs:")
    
    for word, count in unbound_counts.most_common(20):
        print(f"  {word:<10} (Count: {count})")

if __name__ == "__main__":
    with open(r'unbound_words.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        main()
