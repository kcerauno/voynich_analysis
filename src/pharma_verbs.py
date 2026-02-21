import sqlite3
import re
from collections import Counter, defaultdict
import sys

def main():
    db_path = r'data\voynich.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("==============================================================")
    print(" 2. Pharmaceutical Verb Detection (Recipe Instructions) ")
    print("==============================================================")
    
    cursor.execute("""
    SELECT category, page, line_number, word_position, word 
    FROM words_enriched 
    WHERE word IS NOT NULL AND word != ''
    ORDER BY page, line_number, word_position
    """)
    rows = cursor.fetchall()
    
    # Precompute line max
    line_max = defaultdict(int)
    for cat, p, l, pos, w in rows:
        if pos > line_max[(p, l)]:
            line_max[(p, l)] = pos
    
    # Count words per category, filtering by position
    cat_first = defaultdict(Counter)  # Words at position 1 (line-initial)
    cat_all = defaultdict(Counter)
    
    for cat, p, l, pos, w in rows:
        if not cat: continue
        w_clean = re.sub(r'[^a-zA-Z]', '', w)
        if len(w_clean) < 2: continue
        cat_all[cat][w_clean] += 1
        if pos == 1:
            cat_first[cat][w_clean] += 1
    
    pharma = cat_all['pharmaceutical']
    pharma_first = cat_first['pharmaceutical']
    
    non_pharma_cats = ['textonly', 'herbal', 'cosmological', 'astronomical', 'astrology', 'biological']
    non_pharma = Counter()
    non_pharma_first = Counter()
    for cat in non_pharma_cats:
        non_pharma += cat_all[cat]
        non_pharma_first += cat_first[cat]
    
    print(f"\nPharmaceutical section: {sum(pharma.values())} words, {len(pharma)} unique")
    print(f"Non-Pharma sections: {sum(non_pharma.values())} words")
    
    # A. Words exclusive to Pharmaceutical
    exclusive = {}
    for w, cnt in pharma.items():
        if w not in non_pharma and cnt >= 2:
            exclusive[w] = cnt
    
    print(f"\n--- Words EXCLUSIVE to Pharmaceutical (count >= 2) ---")
    for w, cnt in sorted(exclusive.items(), key=lambda x: x[1], reverse=True)[:20]:
        first_cnt = pharma_first.get(w, 0)
        first_pct = (first_cnt / cnt * 100) if cnt else 0
        print(f"  {w:<14}: {cnt} total, {first_cnt} line-initial ({first_pct:.0f}%)")
    
    # B. Words skewed to Pharma AND frequently line-initial
    print(f"\n--- Pharma-Skewed + Line-Initial Words (Recipe Verbs) ---")
    print("(Verbs in recipes start sentences: 'Mix...', 'Boil...', 'Add...')")
    
    verb_candidates = []
    for w, cnt_p in pharma.items():
        cnt_np = non_pharma.get(w, 0)
        total = cnt_p + cnt_np
        if total < 3: continue
        
        pharma_ratio = cnt_p / total
        first_in_pharma = pharma_first.get(w, 0)
        first_ratio = (first_in_pharma / cnt_p) if cnt_p else 0
        
        # Verb candidate: skewed to pharma (>50%) AND frequently line-initial (>20%)
        if pharma_ratio >= 0.5 and first_ratio >= 0.15:
            verb_candidates.append((w, cnt_p, cnt_np, pharma_ratio, first_in_pharma, first_ratio))
    
    verb_candidates.sort(key=lambda x: x[3] * x[5], reverse=True)
    
    print(f"{'Word':<14} | {'Pharma':>6} | {'Other':>5} | {'P_ratio':>7} | {'1st_cnt':>7} | {'1st_pct':>7}")
    print("-" * 65)
    for w, cp, cnp, pr, fc, fr in verb_candidates[:20]:
        print(f"{w:<14} | {cp:>6} | {cnp:>5} | {pr*100:>6.0f}% | {fc:>7} | {fr*100:>6.0f}%")
    
    # C. Unique structural patterns in Pharma vs others
    print(f"\n--- Pharma vs Non-Pharma: Line Length Distribution ---")
    pharma_line_lens = []
    other_line_lens = []
    
    line_words = defaultdict(lambda: defaultdict(list))
    for cat, p, l, pos, w in rows:
        if cat:
            line_words[cat][(p, l)].append(w)
    
    for key, ws in line_words['pharmaceutical'].items():
        pharma_line_lens.append(len(ws))
    for cat in non_pharma_cats:
        for key, ws in line_words[cat].items():
            other_line_lens.append(len(ws))
    
    if pharma_line_lens:
        avg_p = sum(pharma_line_lens) / len(pharma_line_lens)
        avg_o = sum(other_line_lens) / len(other_line_lens)
        print(f"  Pharmaceutical avg words/line: {avg_p:.1f}")
        print(f"  Non-Pharma avg words/line: {avg_o:.1f}")
    
    conn.close()

if __name__ == "__main__":
    with open(r'pharma_verbs.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        main()
