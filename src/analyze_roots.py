import sqlite3
import re
from collections import defaultdict, Counter
import sys

# Most common and structural prefixes/suffixes based on previous analysis
PREFIXES = sorted(['qo', 'ch', 'sh', 'ok', 'ot', 'da', 'o', 'c', 'q', 's', 'd'], key=len, reverse=True)
SUFFIXES = sorted(['dy', 'in', 'ey', 'ol', 'ar', 'y', 'n', 'l', 'r'], key=len, reverse=True)

def extract_root(word):
    prefix = ""
    suffix = ""
    root = word
    
    # Strip prefix
    for p in PREFIXES:
        if root.startswith(p):
            prefix = p
            root = root[len(p):]
            break
            
    # Strip suffix
    for s in SUFFIXES:
        if root.endswith(s):
            suffix = s
            root = root[:-len(s)]
            break
            
    return prefix, root, suffix

def main():
    db_path = r'data\voynich.db'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT word FROM words WHERE word IS NOT NULL AND word != '';")
    words = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # Clean words
    cleaned_words = [re.sub(r'[^a-zA-Z]', '', w) for w in words]
    cleaned_words = [w for w in cleaned_words if len(w) >= 3] # Minimum length to have a sensible prefix+root+suffix combo
    
    root_prefix_counts = defaultdict(Counter)
    root_suffix_counts = defaultdict(Counter)
    prefix_suffix_counts = defaultdict(Counter)
    root_counts = Counter()
    
    for w in cleaned_words:
        p, r, s = extract_root(w)
        if r: # If there's a root left
            root_counts[r] += 1
            if p: root_prefix_counts[r][p] += 1
            if s: root_suffix_counts[r][s] += 1
        if p and s:
            prefix_suffix_counts[p][s] += 1
            
    print("==================================================")
    print(" Root - Prefix/Suffix Correlation Analysis ")
    print("==================================================")
    
    print("\n--- Top 20 Most Frequent Roots ---")
    for r, count in root_counts.most_common(20):
        # Calculate how often this root takes a prefix vs no prefix
        total_p = sum(root_prefix_counts[r].values())
        top_p = root_prefix_counts[r].most_common(2)
        p_str = ", ".join([f"{k}({v})" for k,v in top_p]) if top_p else "None"
        
        # Calculate how often this root takes a suffix
        total_s = sum(root_suffix_counts[r].values())
        top_s = root_suffix_counts[r].most_common(2)
        s_str = ", ".join([f"{k}({v})" for k,v in top_s]) if top_s else "None"
        
        print(f"Root: '{r:<4}' | Freq: {count:<4} | Top Prefixes: {p_str:<20} | Top Suffixes: {s_str}")

    print("\n\n--- Co-occurrence: Prefix <-> Suffix Dependency ---")
    print("Do certain prefixes strongly dictate the suffix regardless of root?")
    for p in ['qo', 'ch', 'sh', 'o', 'c']:
        total_s_for_p = sum(prefix_suffix_counts[p].values())
        if total_s_for_p == 0: continue
        top_s = prefix_suffix_counts[p].most_common(3)
        print(f"\nPrefix '{p}' (Total pairings: {total_s_for_p}):")
        for s, count in top_s:
            pct = (count / total_s_for_p) * 100
            print(f"  -> takes suffix '{s}': {pct:.1f}%")

if __name__ == "__main__":
    with open(r'root_affix_correlation.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        main()
