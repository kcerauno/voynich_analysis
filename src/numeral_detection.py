import sqlite3
import re
from collections import Counter, defaultdict
import sys

def main():
    db_path = r'data\voynich.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("==================================================")
    print(" Numeral Detection: Astronomical Page Analysis ")
    print("==================================================")
    
    # First, let's see what categories exist
    cursor.execute("SELECT DISTINCT category FROM words_enriched WHERE category IS NOT NULL")
    categories = [r[0] for r in cursor.fetchall()]
    print(f"\nAvailable categories: {categories}")
    
    # Count words per category
    for cat in categories:
        cursor.execute("SELECT COUNT(*) FROM words_enriched WHERE category = ?", (cat,))
        cnt = cursor.fetchone()[0]
        print(f"  {cat}: {cnt} words")
    
    # Identify astronomical/zodiac categories
    astro_cats = [c for c in categories if any(kw in c.lower() for kw in ['astro', 'zodiac', 'cosmo', 'star'])]
    if not astro_cats:
        # Fallback: show all categories and pick manually
        print("\nNo obvious 'Astronomical' category found. Trying broader search...")
        astro_cats = [c for c in categories if c.lower() not in ['herbal', 'pharmaceutical', 'biological', 'text', 'textonly']]
        
    print(f"\nTarget categories (potential numerical context): {astro_cats}")
    non_astro_cats = [c for c in categories if c not in astro_cats]
    print(f"Non-target categories: {non_astro_cats}")
    
    # Get all words from astro pages
    astro_words = Counter()
    for cat in astro_cats:
        cursor.execute("""
        SELECT word FROM words_enriched 
        WHERE category = ? AND word IS NOT NULL AND word != ''
        """, (cat,))
        for (w,) in cursor.fetchall():
            w_clean = re.sub(r'[^a-zA-Z]', '', w)
            if len(w_clean) >= 2:
                astro_words[w_clean] += 1
    
    # Get all words from non-astro pages
    non_astro_words = Counter()
    for cat in non_astro_cats:
        cursor.execute("""
        SELECT word FROM words_enriched 
        WHERE category = ? AND word IS NOT NULL AND word != ''
        """, (cat,))
        for (w,) in cursor.fetchall():
            w_clean = re.sub(r'[^a-zA-Z]', '', w)
            if len(w_clean) >= 2:
                non_astro_words[w_clean] += 1
    
    print(f"\nTotal unique words in Astronomical pages: {len(astro_words)}")
    print(f"Total unique words in Non-Astronomical pages: {len(non_astro_words)}")
    
    # Find words EXCLUSIVE to astronomical pages
    exclusive = {}
    for w, cnt in astro_words.items():
        if w not in non_astro_words and cnt >= 2:
            exclusive[w] = cnt
            
    # Find words HEAVILY skewed toward astronomical pages (>80% of occurrences)
    skewed = {}
    for w, cnt_a in astro_words.items():
        cnt_na = non_astro_words.get(w, 0)
        total = cnt_a + cnt_na
        if total >= 5:
            ratio = cnt_a / total
            if ratio >= 0.7:
                skewed[w] = (cnt_a, cnt_na, ratio)
    
    print(f"\n--- Words EXCLUSIVE to Astronomical/Zodiac pages (count >= 2) ---")
    for w, cnt in sorted(exclusive.items(), key=lambda x: x[1], reverse=True)[:30]:
        print(f"  {w:<12}: {cnt} occurrences (ONLY in astronomical pages)")
    
    print(f"\n--- Words HEAVILY SKEWED toward Astronomical pages (>=70%, count >= 5) ---")
    for w, (ca, cna, ratio) in sorted(skewed.items(), key=lambda x: x[1][2], reverse=True)[:30]:
        print(f"  {w:<12}: {ca:>4} astro / {cna:>4} other = {ratio*100:.0f}% astronomical")
    
    # Now let's look at SHORT words (2-4 chars) that are exclusive or skewed
    # These are more likely to be numerals
    print(f"\n--- SHORT (2-4 chars) NUMERAL CANDIDATES ---")
    print("(Short, astronomical-exclusive or skewed words are prime numeral candidates)")
    
    candidates = []
    for w, cnt in exclusive.items():
        if 2 <= len(w) <= 4:
            candidates.append((w, cnt, 0, 1.0, 'EXCLUSIVE'))
    for w, (ca, cna, ratio) in skewed.items():
        if 2 <= len(w) <= 4:
            candidates.append((w, ca, cna, ratio, 'SKEWED'))
    
    candidates.sort(key=lambda x: x[1], reverse=True)
    for w, ca, cna, ratio, kind in candidates[:20]:
        print(f"  {w:<8}: {ca} astro / {cna} other ({ratio*100:.0f}%) [{kind}]")
    
    # Also analyze per-page word frequencies within astronomical sections
    # to see if certain words cluster on specific pages
    print(f"\n--- Per-Page Distribution of Top Astronomical-Exclusive Words ---")
    cursor.execute("""
    SELECT page, word FROM words_enriched 
    WHERE category IN ({}) AND word IS NOT NULL AND word != ''
    """.format(','.join(['?' for _ in astro_cats])), astro_cats)
    
    page_words = defaultdict(Counter)
    for p, w in cursor.fetchall():
        w_clean = re.sub(r'[^a-zA-Z]', '', w)
        if len(w_clean) >= 2:
            page_words[p][w_clean] += 1
    
    # Get top 10 exclusive words and show their per-page distribution
    top_exclusive = sorted(exclusive.items(), key=lambda x: x[1], reverse=True)[:10]
    for w, total in top_exclusive:
        pages_with = []
        for page, wc in page_words.items():
            if w in wc:
                pages_with.append((page, wc[w]))
        pages_with.sort(key=lambda x: x[1], reverse=True)
        page_str = ", ".join(f"{p}({c})" for p, c in pages_with[:5])
        print(f"  {w:<12}: pages -> {page_str}")
    
    conn.close()

if __name__ == "__main__":
    with open(r'numeral_detection.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        main()
