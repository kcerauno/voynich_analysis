import sqlite3
import re
from collections import defaultdict, Counter
import sys
import itertools

# Prefix/Suffix definitions from previous step
PREFIXES = sorted(['qo', 'ch', 'sh', 'ok', 'ot', 'da', 'o', 'c', 'q', 's', 'd'], key=len, reverse=True)
SUFFIXES = sorted(['dy', 'in', 'ey', 'ol', 'ar', 'y', 'n', 'l', 'r'], key=len, reverse=True)

def extract_affixes(word):
    # Cleans word and extracts just the prefix and suffix for transition tracking
    w = re.sub(r'[^a-zA-Z]', '', word)
    if not w: return None, None
    
    p, s = "None", "None"
    
    for prefix in PREFIXES:
        if w.startswith(prefix):
            p = prefix
            break
            
    for suffix in SUFFIXES:
        if w.endswith(suffix):
            s = suffix
            break
            
    return p, s

def main():
    db_path = r'data\voynich.db'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Fetch words ordered by page, line, and position to maintain bigram order
    query = """
    SELECT page, line_number, word_position, word 
    FROM words 
    WHERE word IS NOT NULL AND word != ''
    ORDER BY page, line_number, word_position;
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    # Store transitions
    # prev_suffix -> current_prefix
    suffix_to_prefix = defaultdict(Counter)
    # prev_prefix -> current_prefix
    prefix_to_prefix = defaultdict(Counter)
    
    prev_p = None
    prev_s = None
    prev_page = None
    prev_line = None
    
    for row in rows:
        page, line_num, pos, word = row
        p, s = extract_affixes(word)
        
        if not p and not s:
            prev_p, prev_s = None, None
            continue
            
        # Only consider transitions within the same line to avoid document boundary noise
        if prev_page == page and prev_line == line_num:
            if prev_s and p:
                suffix_to_prefix[prev_s][p] += 1
            if prev_p and p:
                prefix_to_prefix[prev_p][p] += 1
                
        prev_p = p
        prev_s = s
        prev_page = page
        prev_line = line_num

    print("==================================================")
    print(" Voynich Transition (Bigram) Analysis ")
    print("==================================================")
    
    print("\n--- 1. Previous Suffix -> Current Prefix ---")
    print("Does how the last word ended dictate how the new word begins?")
    for s in ['y', 'dy', 'in', 'l', 'r', 'None']:
        total_transitions = sum(suffix_to_prefix[s].values())
        if total_transitions < 100: continue
        
        top_p = suffix_to_prefix[s].most_common(5)
        print(f"\nAfter ending in '-{s}' (N={total_transitions}):")
        for p, count in top_p:
            pct = (count / total_transitions) * 100
            print(f"  -> Next word starts with '{p}-': {pct:.1f}%")
            
    print("\n\n--- 2. Previous Prefix -> Current Prefix ---")
    print("Are prefixes clustered together (e.g., qo followed by another qo)?")
    for p_prev in ['qo', 'ch', 'sh', 'o', 'da', 'None']:
        total_transitions = sum(prefix_to_prefix[p_prev].values())
        if total_transitions < 100: continue
        
        top_p = prefix_to_prefix[p_prev].most_common(5)
        print(f"\nAfter starting with '{p_prev}-' (N={total_transitions}):")
        for p, count in top_p:
            pct = (count / total_transitions) * 100
            print(f"  -> Next word also starts with '{p}-': {pct:.1f}%")

if __name__ == "__main__":
    with open(r'transition_analysis.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        main()
