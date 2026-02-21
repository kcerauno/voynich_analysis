import sqlite3
import re
from collections import Counter, defaultdict
import sys

def main():
    db_path = r'data\voynich.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("==============================================================")
    print(" Full-Text Numeral Candidate Analysis (All Categories) ")
    print("==============================================================")
    
    # Numeral candidates from our previous analyses
    candidates = ['ot', 'os', 'om', 'al', 'ar', 'oto', 'oees', 'eees', 
                  'ees', 'oteos', 'okeos', 'otees', 'alar', 'alal', 'am',
                  'ro', 'ls', 'aim', 'as']
    
    # Get all words with metadata
    cursor.execute("""
    SELECT category, page, line_number, word_position, word 
    FROM words_enriched 
    WHERE word IS NOT NULL AND word != ''
    ORDER BY page, line_number, word_position
    """)
    rows = cursor.fetchall()
    
    # Pre-compute line lengths
    line_max = defaultdict(int)
    for cat, p, l, pos, w in rows:
        key = (p, l)
        if pos > line_max[key]:
            line_max[key] = pos
    
    # 1. Category distribution for each candidate
    print("\n--- 1. Per-Category Distribution of Numeral Candidates ---")
    print(f"{'Word':<10} | {'textonly':>8} | {'herbal':>7} | {'cosmo':>6} | {'astro':>6} | {'astrol':>7} | {'bio':>5} | {'pharma':>7} | {'Total':>6} | {'Astro%':>6}")
    print("-" * 100)
    
    cat_counts = {}
    for cand in candidates:
        counts = defaultdict(int)
        total = 0
        for cat, p, l, pos, w in rows:
            w_clean = re.sub(r'[^a-zA-Z]', '', w)
            if w_clean == cand:
                counts[cat or 'unknown'] += 1
                total += 1
        
        if total == 0: continue
        
        astro_total = counts.get('astronomical', 0) + counts.get('cosmological', 0) + counts.get('astrology', 0)
        astro_pct = (astro_total / total * 100) if total else 0
        
        cat_counts[cand] = (counts, total, astro_pct)
        
        print(f"{cand:<10} | "
              f"{counts.get('textonly', 0):>8} | "
              f"{counts.get('herbal', 0):>7} | "
              f"{counts.get('cosmological', 0):>6} | "
              f"{counts.get('astronomical', 0):>6} | "
              f"{counts.get('astrology', 0):>7} | "
              f"{counts.get('biological', 0):>5} | "
              f"{counts.get('pharmaceutical', 0):>7} | "
              f"{total:>6} | "
              f"{astro_pct:>5.1f}%")
    
    # 2. Line position analysis (First/Middle/Last) for candidates
    print("\n--- 2. Line Position Behavior of Numeral Candidates ---")
    print(f"{'Word':<10} | {'First%':>7} | {'Middle%':>8} | {'Last%':>7} | {'Total':>6}")
    print("-" * 55)
    
    for cand in candidates:
        total = 0; first = 0; middle = 0; last = 0
        for cat, p, l, pos, w in rows:
            w_clean = re.sub(r'[^a-zA-Z]', '', w)
            if w_clean != cand: continue
            total += 1
            mx = line_max[(p, l)]
            if pos == 1: first += 1
            elif pos == mx: last += 1
            else: middle += 1
        
        if total == 0: continue
        pf = first / total * 100
        pm = middle / total * 100
        pl = last / total * 100
        print(f"{cand:<10} | {pf:>6.1f}% | {pm:>7.1f}% | {pl:>6.1f}% | {total:>6}")
    
    # 3. Co-occurrence: what words appear immediately BEFORE and AFTER candidates?
    print("\n--- 3. Context Words (What appears next to numeral candidates?) ---")
    
    # Build ordered word stream per page
    page_lines = defaultdict(lambda: defaultdict(list))
    for cat, p, l, pos, w in rows:
        w_clean = re.sub(r'[^a-zA-Z]', '', w)
        if len(w_clean) >= 1:
            page_lines[p][l].append((pos, w_clean))
    
    # Build flat stream per page
    for cand in ['ot', 'os', 'om', 'al', 'ar', 'oto', 'oteos', 'am']:
        before = Counter()
        after = Counter()
        
        for p in page_lines:
            for l in sorted(page_lines[p].keys()):
                words_in_line = [w for _, w in sorted(page_lines[p][l])]
                for i, w in enumerate(words_in_line):
                    if w == cand:
                        if i > 0: before[words_in_line[i-1]] += 1
                        if i < len(words_in_line) - 1: after[words_in_line[i+1]] += 1
        
        total_ctx = sum(before.values()) + sum(after.values())
        if total_ctx == 0: continue
        
        top_before = before.most_common(3)
        top_after = after.most_common(3)
        
        b_str = ", ".join(f"{w}({c})" for w, c in top_before)
        a_str = ", ".join(f"{w}({c})" for w, c in top_after)
        
        print(f"\n  '{cand}' (Total context: {total_ctx}):")
        print(f"    BEFORE: {b_str}")
        print(f"    AFTER:  {a_str}")
    
    # 4. Benford's Law test: do candidates follow numeral-like frequency decay?
    print("\n--- 4. Frequency Decay Pattern (Benford's Law Test) ---")
    print("If these are numerals (1,2,3...), smaller numbers should be more frequent.")
    
    freq_sorted = [(c, cat_counts[c][1]) for c in candidates if c in cat_counts]
    freq_sorted.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\nRanked by frequency:")
    for i, (w, cnt) in enumerate(freq_sorted):
        bar = '#' * min(cnt, 60)
        print(f"  {i+1:>2}. {w:<10} {cnt:>4} {bar}")
    
    conn.close()

if __name__ == "__main__":
    with open(r'fulltext_numeral.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        main()
