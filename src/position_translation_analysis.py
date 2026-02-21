import sqlite3
import sys
from collections import defaultdict

def main():
    db_path = r'data\voynich.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("==================================================")
    print(" Syntactic Positional Analysis of Translated Dialects ")
    print("==================================================")
    
    # Pre-fetch all words to avoid slow subqueries
    query = """
    SELECT language, page, line_number, word_position, word 
    FROM words_enriched 
    WHERE word IS NOT NULL AND word != ''
    ORDER BY language, page, line_number, word_position
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    
    # Calculate max positions per line
    line_lengths = defaultdict(int)
    for lang, p, l, pos, w in rows:
        key = (lang, p, l)
        if pos > line_lengths[key]:
            line_lengths[key] = pos
            
    # Pair tests: [Lang, Word]
    pairs = [
        (('B', 'qo', False), ('A', 'okey', False)),
        (('B', 'qo', False), ('A', 'okeol', False)),
        (('B', 'dy', False), ('A', 'kchy', False)),
        (('A', 'chol', False), ('B', 'ycheol', False)),
        (('B', 'qo', True), ('A', 'ok', True)), # Prefix test
        (('A', 'ch', True), ('B', 'qot', True)) # Prefix test
    ]
    
    for (l1, w1, is_prefix1), (l2, w2, is_prefix2) in pairs:
        
        def get_stats(target_lang, target_word, is_prefix):
            total = 0
            first = 0
            last = 0
            for lang, p, l, pos, w in rows:
                if lang != target_lang: continue
                
                match = False
                if is_prefix and w.startswith(target_word): match = True
                elif not is_prefix and w == target_word: match = True
                
                if match:
                    total += 1
                    if pos == 1: first += 1
                    if pos == line_lengths[(lang, p, l)]: last += 1
            return total, first, last

        t1, f1, last1 = get_stats(l1, w1, is_prefix1)
        t2, f2, last2 = get_stats(l2, w2, is_prefix2)
        
        if t1 == 0 or t2 == 0: continue
            
        p_f1 = (f1 / t1) * 100
        p_l1 = (last1 / t1) * 100
        
        p_f2 = (f2 / t2) * 100
        p_l2 = (last2 / t2) * 100
        
        print(f"\n--- Translated Pair: [{l1}] '{w1}' <====> [{l2}] '{w2}' ---")
        print(f"[{l1}] {w1}: First on line: {p_f1:05.1f}% | Last on line: {p_l1:05.1f}%  (Total {t1})")
        print(f"[{l2}] {w2}: First on line: {p_f2:05.1f}% | Last on line: {p_l2:05.1f}%  (Total {t2})")
        
        diff_first = abs(p_f1 - p_f2)
        diff_last = abs(p_l1 - p_l2)
        
        if diff_first < 10 and diff_last < 10:
            print(">>> BEHAVIOR MATCH: Both words share strongly similar spatial formatting rules.")
        else:
            print(">>> BEHAVIOR MISMATCH: They mean the same thing conceptually, but are formatted differently.")

    conn.close()

if __name__ == "__main__":
    with open(r'position_translation_analysis.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        main()
