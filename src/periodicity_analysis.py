import sqlite3
import re
from collections import defaultdict
import numpy as np
import sys

def main():
    db_path = r'data\voynich.db'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # We want the text in exact, unbroken sequence to measure absolute distances
    query = """
    SELECT page, line_number, word_position, word 
    FROM words 
    WHERE word IS NOT NULL AND word != ''
    ORDER BY page, line_number, word_position;
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    # Create an unbroken stream of words
    stream = []
    for row in rows:
        w_clean = re.sub(r'[^a-zA-Z]', '', row[3])
        if w_clean:
            stream.append(w_clean)
            
    print("==================================================")
    print(" 3. Distance and Periodicity Analysis ")
    print("==================================================")
    print(f"Total words in unbroken stream: {len(stream)}")
    
    # We will test a few very common patterns to see if they pulse at a regular beat.
    # e.g., 'qo', '-dy', '-y'
    targets = {
        'starts_qo': lambda w: w.startswith('qo'),
        'ends_dy': lambda w: w.endswith('dy'),
        'ends_y': lambda w: w.endswith('y'),
        'contains_ch': lambda w: 'ch' in w
    }
    
    results = {}
    
    for label, condition in targets.items():
        # Find all absolute indices where this condition is met
        indices = [i for i, w in enumerate(stream) if condition(w)]
        
        if len(indices) < 100:
            continue
            
        # Calculate distances between consecutive occurrences
        distances = np.diff(indices)
        
        # We look for the most common distances (the "beat")
        unique, counts = np.unique(distances, return_counts=True)
        dist_counts = sorted(zip(unique, counts), key=lambda x: x[1], reverse=True)
        
        results[label] = {
            'total': len(indices),
            'avg_dist': np.mean(distances),
            'median_dist': np.median(distances),
            'top_distances': dist_counts[:5] # Top 5 most common intervals
        }
        
    for label, data in results.items():
        print(f"\n--- Analysis for: {label} ---")
        print(f"Total occurrences: {data['total']}")
        print(f"Average distance: {data['avg_dist']:.1f} words")
        print(f"Median distance: {data['median_dist']:.1f} words")
        
        print("Top 5 exact intervals (Distance -> Count):")
        for dist, count in data['top_distances']:
            percentage = (count / len(stream)) * 100
            print(f"  Every {dist} words -> happened {count} times")
            
        # Check for very tight repetition (echoing immediately)
        echoes = sum(c for d, c in data['top_distances'] if d == 1)
        if echoes > 0:
            print(f"  * Note: Occurs consecutively (echoes itself) {echoes} times!")

    print("\n--- Conclusion ---")
    print("If the top interval is highly dominant (e.g., 'every 2 words'), the text is highly mechanical or rhythmic.")
    print("Natural languages have an exponential decay in distance (distance 1 or 2 is common, trailing off).")
    print("If we see spikes at distances like 4, 5, or 6, it implies a rigid cipher structure or musical meter.")

if __name__ == "__main__":
    with open(r'periodicity_analysis.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        main()
