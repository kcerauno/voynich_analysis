import sqlite3
import re
from collections import Counter, defaultdict
import sys

def main():
    db_path = r'data\voynich.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("==================================================")
    print(" Approach 5: Zodiac Page Label Cross-Reference ")
    print("==================================================")
    
    # Known zodiac pages in the Voynich manuscript (f70v-f73v area)
    # These pages have nymphs arranged in concentric circles with star groups
    # The zodiac pages typically include: f70v, f71r, f71v, f72r, f72v, f73r, f73v
    # Also f67r, f67v, f68r, f68v are astronomical with star diagrams
    
    # Get all words from astronomical/cosmological/astrology pages
    cursor.execute("""
    SELECT page, line_number, word_position, word, category
    FROM words_enriched 
    WHERE category IN ('astronomical', 'cosmological', 'astrology')
    AND word IS NOT NULL AND word != ''
    ORDER BY page, line_number, word_position
    """)
    rows = cursor.fetchall()
    
    # Group by page
    page_data = defaultdict(list)
    for p, l, pos, w, cat in rows:
        w_clean = re.sub(r'[^a-zA-Z]', '', w)
        if len(w_clean) >= 2:
            page_data[p].append((l, pos, w_clean))
    
    print(f"\nAstronomical/Cosmological/Astrology pages found: {len(page_data)}")
    
    # For each page, extract:
    # 1. Label words (lines with 1-2 words only)
    # 2. Total unique words
    # 3. Count of short words (2-4 chars, potential numerals)
    
    # Known zodiac signs have specific star counts in Voynich:
    # (This is from published Voynich research)
    # These are approximate known star counts per zodiac section
    zodiac_star_counts = {
        'f70v1': 29, 'f70v2': 30,  # Pisces area
        'f71r': 15, 'f71v': 17,    # Aries area
        'f72r1': 30, 'f72r2': 30, 'f72r3': 29,  # Taurus area
        'f72v1': 17, 'f72v2': 17, 'f72v3': 30,   # Gemini area
        'f73r': 0, 'f73v': 0      # difficult to count
    }
    
    print(f"\n--- Per-Page Analysis of Astronomical Sections ---")
    print(f"{'Page':<10} | {'Total':>5} | {'Labels':>6} | {'Short':>5} | {'Top Label Words'}")
    print("-" * 80)
    
    for page in sorted(page_data.keys()):
        words_on_page = page_data[page]
        
        # Calculate words per line
        lines = defaultdict(list)
        for l, pos, w in words_on_page:
            lines[l].append(w)
        
        # Labels: lines with 1-2 words
        label_words = []
        for l, ws in lines.items():
            if len(ws) <= 2:
                label_words.extend(ws)
        
        # Short words (2-4 chars)
        short_words = [w for _, _, w in words_on_page if 2 <= len(w) <= 4]
        
        # Top label words
        label_counter = Counter(label_words)
        top_labels = label_counter.most_common(5)
        top_str = ", ".join(f"{w}({c})" for w, c in top_labels)
        
        total = len(words_on_page)
        n_labels = len(label_words)
        n_short = len(short_words)
        
        print(f"{page:<10} | {total:>5} | {n_labels:>6} | {n_short:>5} | {top_str}")
    
    # Now cross-reference: for pages with known star counts,
    # see if any word appears exactly that many times
    print(f"\n--- Star Count Cross-Reference ---")
    print("Checking if any word's frequency matches the known star count on zodiac pages.")
    
    for page, star_count in zodiac_star_counts.items():
        if page not in page_data or star_count == 0:
            continue
            
        word_counts = Counter(w for _, _, w in page_data[page])
        
        # Check for words appearing exactly star_count times
        exact_matches = [w for w, c in word_counts.items() if c == star_count]
        
        # Also check for words appearing close to star_count (+-2)
        close_matches = [(w, c) for w, c in word_counts.items() 
                        if abs(c - star_count) <= 2 and c >= 3]
        
        print(f"\n  Page {page} (Expected stars: {star_count}):")
        if exact_matches:
            print(f"    EXACT MATCH: {exact_matches}")
        if close_matches:
            for w, c in sorted(close_matches, key=lambda x: abs(x[1]-star_count)):
                print(f"    Close: '{w}' appears {c} times (diff: {c-star_count:+d})")
        
        # Also show the most frequent words on this page for context
        print(f"    Top 5 words: {word_counts.most_common(5)}")
    
    # Finally, check if label words on zodiac pages form a counting sequence
    print(f"\n--- Label Sequence Analysis on Zodiac Pages ---")
    print("Looking for sequences of distinct labels that could be sequential numbers.")
    
    for page in sorted(page_data.keys()):
        if page not in zodiac_star_counts: continue
        
        words_on_page = page_data[page]
        lines = defaultdict(list)
        for l, pos, w in words_on_page:
            lines[l].append(w)
        
        # Get only label lines in order
        label_sequence = []
        for l in sorted(lines.keys()):
            ws = lines[l]
            if len(ws) <= 2:
                label_sequence.extend(ws)
        
        if label_sequence:
            unique_labels = list(dict.fromkeys(label_sequence))  # preserve order, remove dups
            print(f"\n  Page {page}: Label sequence ({len(label_sequence)} words, {len(unique_labels)} unique):")
            print(f"    {' -> '.join(unique_labels[:15])}")
    
    conn.close()

if __name__ == "__main__":
    with open(r'zodiac_crossref.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        main()
