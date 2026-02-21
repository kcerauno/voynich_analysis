import sqlite3
import re
from collections import defaultdict, Counter
import sys

# Define Gallows characters ( EVA: p, t, k, f )
GALLOWS = {'p', 't', 'k', 'f'}

def main():
    db_path = r'data\voynich.db'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # We need page, line_number, and the words.
    # To determine paragraphs, we'll assume line_number = 1 is the start of a paragraph/page.
    # In many transliterations, sudden jumps in line numbering or new pages denote new paragraphs.
    # For a robust approach, we'll look at the first line of every page (line_number = 1).
    query = """
    SELECT page, line_number, word 
    FROM words 
    WHERE word IS NOT NULL AND word != ''
    ORDER BY page, line_number, word_position;
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    print("==================================================")
    print(" 1. Paragraph Position & Gallows Character Analysis ")
    print("==================================================")
    
    total_gallows = 0
    gallows_on_first_line = 0
    gallows_on_other_lines = 0
    
    # Count lines to calculate averages
    first_lines_count = 0
    other_lines_count = 0
    
    # Track which specific lines they appear on
    current_page = None
    current_line = None
    is_first_line = False
    
    # Group words by (page, line)
    lines_dict = defaultdict(list)
    for p, l, w in rows:
        w_clean = re.sub(r'[^a-zA-Z]', '', w)
        if w_clean:
            lines_dict[(p, l)].append(w_clean)
            
    # Now analyze the grouped lines
    for (page, line_num), words in lines_dict.items():
        # A simple heuristic: line_number 1 is definitely the start of a block/paragraph.
        # Alternatively, if line numbering resets per paragraph in the db, line 1 is the key.
        if line_num == 1:
            is_first_line = True
            first_lines_count += 1
        else:
            is_first_line = False
            other_lines_count += 1
            
        # Count gallows in this line
        line_joined = "".join(words)
        gallows_in_line = sum(1 for char in line_joined if char in GALLOWS)
        
        total_gallows += gallows_in_line
        if is_first_line:
            gallows_on_first_line += gallows_in_line
        else:
            gallows_on_other_lines += gallows_in_line

    if total_gallows == 0 or first_lines_count == 0 or other_lines_count == 0:
        print("Not enough data to perform analysis.")
        return
        
    avg_first = gallows_on_first_line / first_lines_count
    avg_other = gallows_on_other_lines / other_lines_count
    
    print(f"Total Gallows Characters (p, t, k, f): {total_gallows}")
    print(f"\n--- Distribution ---")
    print(f"Total 'First Lines' analyzed: {first_lines_count}")
    print(f"Total 'Other Lines' analyzed: {other_lines_count}")
    
    print(f"\nGallows on First Lines:  {gallows_on_first_line} ({gallows_on_first_line/total_gallows*100:.1f}%)")
    print(f"Gallows on Other Lines: {gallows_on_other_lines} ({gallows_on_other_lines/total_gallows*100:.1f}%)")
    
    print(f"\n--- Density (Gallows per Line) ---")
    print(f"Average Gallows per 'First Line':  {avg_first:.2f} characters")
    print(f"Average Gallows per 'Other Line':  {avg_other:.2f} characters")
    
    ratio = avg_first / avg_other if avg_other > 0 else 0
    print(f"\n>>> Density Ratio: A 'First Line' has {ratio:.1f}x more gallows characters than a normal line.")
    
    print("\n--- Conclusion ---")
    if ratio > 2.0:
        print("STRONG CORRELATION: Gallows characters are overwhelmingly concentrated at the start of paragraphs/pages.")
        print("This strongly supports the hypothesis that they function as structural drop-caps, ornamental markers, or cipher shift-keys, rather than standard phonetic consonants.")
    else:
        print("WEAK/NO CORRELATION: Gallows characters are relatively evenly distributed. They likely function as standard letters within the text.")

if __name__ == "__main__":
    with open(r'gallows_analysis.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        main()
