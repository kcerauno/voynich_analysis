import sqlite3
import re
from collections import defaultdict, Counter
import sys

# High frequency, highly predictable affixes (Likely Nulls / Structural scaffolding)
NULL_PREFIXES = sorted(['qo', 'ch', 'sh', 'o', 'q', 'c', 's'], key=len, reverse=True)
NULL_SUFFIXES = sorted(['dy', 'in', 'ey', 'y', 'n', 'l', 'r'], key=len, reverse=True)

def strip_nulls(word):
    w = word
    stripped_p = False
    stripped_s = False
    
    # Strip prefix
    for p in NULL_PREFIXES:
        if w.startswith(p):
            w = w[len(p):]
            stripped_p = True
            break
            
    # Strip suffix
    for s in NULL_SUFFIXES:
        if w.endswith(s):
            w = w[:-len(s)]
            stripped_s = True
            break
            
    return w, stripped_p, stripped_s

def main():
    db_path = r'data\voynich.db'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT word FROM words WHERE word IS NOT NULL AND word != '';")
    words = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    cleaned_words = [re.sub(r'[^a-zA-Z]', '', w) for w in words]
    cleaned_words = [w for w in cleaned_words if len(w) >= 2] # Need at least 2 chars to be meaningful
    
    core_texts = []
    fully_stripped_count = 0
    
    for w in cleaned_words:
        core, sp, ss = strip_nulls(w)
        if len(core) > 0:
            core_texts.append(core)
        if len(core) == 0 and sp and ss: # Revolved entirely into nothing (e.g. qody -> qo + dy = "")
            fully_stripped_count += 1

    core_counts = Counter(core_texts)
    
    total_valid = len(cleaned_words)
    total_core_retained = len(core_texts)
    
    print("==================================================")
    print(" 2. Core Text Extraction (Null Binding Reduction) ")
    print("==================================================")
    print("Hypothesis: Highly predictable, high-frequency affixes (like 'qo' or 'dy') are meaningless Nulls or structural scaffolding. If we strip them, what is the 'Core' vocabulary left behind?")
    
    print(f"\nTotal words analyzed: {total_valid}")
    print(f"Words completely annihilated into nothing (e.g., 'qody'): {fully_stripped_count} ({(fully_stripped_count/total_valid)*100:.1f}%)")
    print(f"Words with a remaining 'Core Text': {total_core_retained}")
    
    print("\n--- The Top 25 Most Frequent 'Core' Stems ---")
    print("If Voynichese is heavily encrypted with Null padding, these remaining stems are the true information.")
    
    for core, count in core_counts.most_common(25):
        print(f"  {core:<10} (Count: {count})")
        
    print("\n--- Long Core Stems (Length >= 4) ---")
    long_cores = {k: v for k, v in core_counts.items() if len(k) >= 4}
    long_core_counts = Counter(long_cores)
    for core, count in long_core_counts.most_common(10):
        print(f"  {core:<15} (Count: {count})")

if __name__ == "__main__":
    with open(r'core_text_analysis.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        main()
