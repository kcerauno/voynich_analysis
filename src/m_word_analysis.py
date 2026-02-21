import sqlite3
import re
from collections import defaultdict, Counter
import sys

def main():
    db_path = r'data\voynich.db'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Query words including metadata
    query = """
    SELECT page, word_position, word, category, language, scribe 
    FROM words_enriched 
    WHERE word IS NOT NULL AND word != '';
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    
    # Also get max positions for line end logic
    query_max = """
    SELECT page, line_number, MAX(word_position) 
    FROM words_enriched 
    GROUP BY page, line_number;
    """
    cursor.execute(query_max)
    max_pos_map = {(row[0], row[1]): row[2] for row in cursor.fetchall()}
    
    # Need line_number in rows, adding a second query
    query2 = """
    SELECT page, line_number, word_position, word, category, language, scribe 
    FROM words_enriched 
    WHERE word IS NOT NULL AND word != '';
    """
    cursor.execute(query2)
    rows2 = cursor.fetchall()
    
    conn.close()
    
    m_words = []
    total_cleaned = 0
    
    # Track distributions
    cat_m = Counter()
    lang_m = Counter()
    scribe_m = Counter()
    pos_m = Counter()
    page_m = Counter()
    
    # Specific M word instances to show context
    m_word_examples = []

    for row in rows2:
        page, line_number, pos, word, cat, lang, scribe = row
        w = re.sub(r'[^a-zA-Z]', '', word)
        if len(w) >= 3:
            total_cleaned += 1
            if w.endswith('m'):
                m_words.append(w)
                cat_m[cat] += 1
                lang_m[lang] += 1
                scribe_m[scribe] += 1
                page_m[page] += 1
                
                max_pos = max_pos_map.get((page, line_number), pos)
                if pos == 1:
                    pos_m['First'] += 1
                elif pos == max_pos and max_pos > 1:
                    pos_m['Last'] += 1
                else:
                    pos_m['Middle'] += 1
                    
                m_word_examples.append((w, page))
                
    total_m = len(m_words)

    print("==================================================")
    print(" Deep Dive Analysis: The 'm'-ending Words ")
    print("==================================================")
    print(f"Total valid words (len>=3): {total_cleaned}")
    print(f"Total 'm'-ending words found: {total_m}")
    print(f"Percentage of total words: {(total_m / total_cleaned) * 100:.2f}%")
    
    m_counts = Counter(m_words)
    print("\n--- Top 20 'm'-Words ---")
    for w, c in m_counts.most_common(20):
        print(f"  {w:<10}  Count: {c}")
        
    print("\n--- Distribution by Category ---")
    for c, count in cat_m.most_common():
        if c: print(f"  {c:<15}: {count:>4} ({(count/total_m)*100:.1f}%)")
        
    print("\n--- Distribution by Language ---")
    for l, count in lang_m.most_common():
        if l: print(f"  {l:<15}: {count:>4} ({(count/total_m)*100:.1f}%)")
        
    print("\n--- Distribution by Line Position ---")
    for p, count in pos_m.most_common():
        print(f"  {p:<15}: {count:>4} ({(count/total_m)*100:.1f}%)")
        
    print("\n--- Top 15 Pages with 'm'-Words ---")
    # This might reveal if they are clustered on specific labels or maps
    page_m_sorted = sorted(page_m.items(), key=lambda x: x[1], reverse=True)
    for p, count in page_m_sorted[:15]:
        print(f"  Page {p:<10}: {count} occurrences")
        
    print("\n--- Context: Examples of 'am' vs 'om' ---")
    am_count = sum(1 for w in m_words if w.endswith('am'))
    om_count = sum(1 for w in m_words if w.endswith('om'))
    print(f"  Words ending in '-am': {am_count}")
    print(f"  Words ending in '-om': {om_count}")

if __name__ == "__main__":
    with open(r'm_word_analysis.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        main()
