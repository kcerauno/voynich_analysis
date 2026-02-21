import sqlite3
import re
from collections import Counter, defaultdict
import sys

def main():
    db_path = r'data\voynich.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("==============================================================")
    print(" 1. Color Term Detection: Herbal-Exclusive Words ")
    print("==============================================================")
    
    # Get word counts per category
    cursor.execute("""
    SELECT category, word FROM words_enriched 
    WHERE word IS NOT NULL AND word != '' AND category IS NOT NULL
    """)
    
    cat_words = defaultdict(Counter)
    for cat, w in cursor.fetchall():
        w_clean = re.sub(r'[^a-zA-Z]', '', w)
        if len(w_clean) >= 2:
            cat_words[cat][w_clean] += 1
    
    herbal = cat_words['herbal']
    non_herbal_cats = ['textonly', 'cosmological', 'astronomical', 'astrology', 'biological', 'pharmaceutical']
    
    non_herbal = Counter()
    for cat in non_herbal_cats:
        non_herbal += cat_words[cat]
    
    print(f"\nHerbal section: {sum(herbal.values())} total words, {len(herbal)} unique")
    print(f"Non-Herbal sections: {sum(non_herbal.values())} total words, {len(non_herbal)} unique")
    
    # A. Words EXCLUSIVE to Herbal (not in any other section)
    exclusive = {}
    for w, cnt in herbal.items():
        if w not in non_herbal and cnt >= 2:
            exclusive[w] = cnt
    
    print(f"\n--- Words EXCLUSIVE to Herbal (count >= 2) ---")
    for w, cnt in sorted(exclusive.items(), key=lambda x: x[1], reverse=True)[:25]:
        print(f"  {w:<14}: {cnt} (HERBAL ONLY)")
    
    # B. Words HEAVILY skewed toward Herbal (>=70%)
    skewed = {}
    for w, cnt_h in herbal.items():
        cnt_nh = non_herbal.get(w, 0)
        total = cnt_h + cnt_nh
        if total >= 5:
            ratio = cnt_h / total
            if ratio >= 0.6:
                skewed[w] = (cnt_h, cnt_nh, ratio)
    
    print(f"\n--- Words SKEWED toward Herbal (>=60%, count >= 5) ---")
    for w, (ch, cnh, r) in sorted(skewed.items(), key=lambda x: x[1][2], reverse=True)[:25]:
        print(f"  {w:<14}: {ch:>3} herbal / {cnh:>3} other = {r*100:.0f}% herbal")
    
    # C. Short herbal-exclusive candidates (color terms are usually short)  
    print(f"\n--- SHORT (2-5 chars) Herbal-Exclusive/Skewed Candidates ---")
    print("(Color adjectives are typically short in most languages)")
    
    short_cands = []
    for w, cnt in exclusive.items():
        if 2 <= len(w) <= 5:
            short_cands.append((w, cnt, 0, 1.0, 'EXCLUSIVE'))
    for w, (ch, cnh, r) in skewed.items():
        if 2 <= len(w) <= 5:
            short_cands.append((w, ch, cnh, r, 'SKEWED'))
    
    short_cands.sort(key=lambda x: x[1], reverse=True)
    for w, ch, cnh, r, kind in short_cands[:15]:
        print(f"  {w:<8}: {ch} herbal / {cnh} other ({r*100:.0f}%) [{kind}]")
    
    # D. Compare with Pharmaceutical (which also deals with plants)
    pharma = cat_words['pharmaceutical']
    print(f"\n--- Cross-check: Herbal-exclusive vs Pharmaceutical presence ---")
    for w, cnt in sorted(exclusive.items(), key=lambda x: x[1], reverse=True)[:15]:
        p_cnt = pharma.get(w, 0)
        print(f"  {w:<14}: Herbal={cnt}, Pharma={p_cnt}")
    
    conn.close()

if __name__ == "__main__":
    with open(r'color_terms.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        main()
