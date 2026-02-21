import sqlite3
import re
from collections import Counter
import sys

def get_word_data(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # We will try to distinguish "Labels" vs "Paragraph Text".
    # Since we don't have explicit bounding boxes in this DB, we can use the 'word_position' and max words per line.
    # Lines with only 1 or 2 words total are very often labels next to stars/plants.
    # Lines with many words (>5) are solid paragraphs.
    
    query = """
    SELECT page, line_number, word_position, word 
    FROM words 
    WHERE word IS NOT NULL AND word != ''
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    
    # Calculate words per line
    words_per_line = Counter()
    for p, l, pos, w in rows:
        words_per_line[(p, l)] = max(words_per_line[(p, l)], pos)
        
    labels = []
    paragraphs = []
    
    for p, l, pos, w in rows:
        w_clean = re.sub(r'[^a-zA-Z]', '', w)
        if len(w_clean) < 2: continue
        
        line_length = words_per_line[(p, l)]
        
        if line_length <= 2:
            labels.append(w_clean)
        elif line_length >= 5:
            paragraphs.append(w_clean)
            
    conn.close()
    return labels, paragraphs

def analyze_affixes(word_list):
    null_prefixes = ['qo', 'ch', 'sh']
    null_suffixes = ['dy', 'in', 'ey', 'y']
    
    has_p = 0
    has_s = 0
    num_words = len(word_list)
    
    for w in word_list:
        if any(w.startswith(p) for p in null_prefixes):
            has_p += 1
        if any(w.endswith(s) for s in null_suffixes):
            has_s += 1
            
    return has_p / num_words if num_words else 0, has_s / num_words if num_words else 0

def main():
    db_path = r'data\voynich.db'
    labels, paragraphs = get_word_data(db_path)
    
    print("==================================================")
    print(" 4. Cross-analysis: Labels vs. Paragraph Context ")
    print("==================================================")
    print(f"Isolated Label Words (Lines with 1-2 words): {len(labels)}")
    print(f"Paragraph Words (Lines with 5+ words): {len(paragraphs)}")
    
    if not labels or not paragraphs:
        print("Not enough data to categorize labels vs paragraphs.")
        return
        
    p_p_ratio, p_s_ratio = analyze_affixes(paragraphs)
    l_p_ratio, l_s_ratio = analyze_affixes(labels)
    
    print("\n--- Morphological Difference ---")
    print(f"Paragraph Words having common 'Null' Prefix ('qo', 'ch', 'sh'): {p_p_ratio*100:.1f}%")
    print(f"Label Words having common 'Null' Prefix ('qo', 'ch', 'sh'):     {l_p_ratio*100:.1f}%")
    print()
    print(f"Paragraph Words having common 'Null' Suffix ('dy', 'in', 'y'): {p_s_ratio*100:.1f}%")
    print(f"Label Words having common 'Null' Suffix ('dy', 'in', 'y'):     {l_s_ratio*100:.1f}%")
    
    # Top words
    print("\n--- Top 15 Paragraph Words ---")
    for w, c in Counter(paragraphs).most_common(15):
        print(f"  {w:<10}: {c}")
        
    print("\n--- Top 15 Label Words ---")
    for w, c in Counter(labels).most_common(15):
        print(f"  {w:<10}: {c}")

if __name__ == "__main__":
    with open(r'label_analysis.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        main()
