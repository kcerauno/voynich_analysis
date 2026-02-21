import sqlite3
import re
from collections import defaultdict, Counter
import sys

PREFIXES = sorted(['qo', 'ch', 'sh', 'ok', 'ot', 'da', 'o', 'c', 'q', 's', 'd'], key=len, reverse=True)
SUFFIXES = sorted(['dy', 'in', 'ey', 'ol', 'ar', 'y', 'n', 'l', 'r'], key=len, reverse=True)

def extract_affixes(word):
    w = re.sub(r'[^a-zA-Z]', '', word)
    if not w: return None, None
    p, s = "None", "None"
    for prefix in PREFIXES:
        if w.startswith(prefix): p = prefix; break
    for suffix in SUFFIXES:
        if w.endswith(suffix): s = suffix; break
    return p, s

def main():
    db_path = r'data\voynich.db'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # We need to know if a word is First, Last, or Middle.
    # To find 'Last', we need the max word_position per line.
    query = """
    SELECT w.page, w.line_number, w.word_position, w.word,
           (SELECT MAX(word_position) 
            FROM words w2 
            WHERE w2.page = w.page AND w2.line_number = w.line_number) as max_pos
    FROM words w
    WHERE w.word IS NOT NULL AND w.word != '';
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    # Counters for position: 'first', 'middle', 'last'
    prefix_pos = {'first': Counter(), 'middle': Counter(), 'last': Counter()}
    suffix_pos = {'first': Counter(), 'middle': Counter(), 'last': Counter()}
    
    total_pos = {'first': 0, 'middle': 0, 'last': 0}
    
    for row in rows:
        page, line, pos, word, max_pos = row
        p, s = extract_affixes(word)
        
        if pos == 1:
            position_tag = 'first'
        elif pos == max_pos and max_pos > 1:
            position_tag = 'last'
        else:
            position_tag = 'middle'
            
        total_pos[position_tag] += 1
        if p: prefix_pos[position_tag][p] += 1
        if s: suffix_pos[position_tag][s] += 1

    print("==================================================")
    print(" Voynich Line Positional Analysis ")
    print("==================================================")
    
    # Print Prefix Distribution
    print("\n--- Prefix Distribution by Line Position ---")
    for pos_tag in ['first', 'middle', 'last']:
        N = total_pos[pos_tag]
        print(f"\nPosition: {pos_tag.upper()} (Total words: {N})")
        for fix, count in prefix_pos[pos_tag].most_common(5):
            pct = (count / N) * 100
            print(f"  {fix:>5}: {pct:>5.1f}%")
            
    # Print Suffix Distribution
    print("\n\n--- Suffix Distribution by Line Position ---")
    for pos_tag in ['first', 'middle', 'last']:
        N = total_pos[pos_tag]
        print(f"\nPosition: {pos_tag.upper()} (Total words: {N})")
        for fix, count in suffix_pos[pos_tag].most_common(5):
            pct = (count / N) * 100
            print(f"  {fix:>5}: {pct:>5.1f}%")

if __name__ == "__main__":
    with open(r'positional_analysis.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        main()
