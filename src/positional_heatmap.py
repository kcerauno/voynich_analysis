import sqlite3
import sys
from collections import defaultdict

def main():
    db_path = r'data\voynich.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    query = """
    SELECT language, page, line_number, word_position, word 
    FROM words_enriched 
    WHERE word IS NOT NULL AND word != ''
    ORDER BY language, page, line_number, word_position
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    # Precompute max word_position per line
    line_max = defaultdict(int)
    for lang, p, l, pos, w in rows:
        key = (lang, p, l)
        if pos > line_max[key]:
            line_max[key] = pos
    
    # Define the affixes to test
    prefixes = ['qo', 'ch', 'sh', 'ok', 'ot', 'da', 'qot', 'qok']
    suffixes = ['dy', 'in', 'ey', 'ol', 'y', 'am', 'ar', 'al']
    
    # For each language x affix, count: total, first, middle, last
    # position_type: 'first' if word_position == 1, 'last' if word_position == max, else 'middle'
    
    results = {}
    
    for lang in ['A', 'B']:
        for prefix in prefixes:
            key = (lang, f'{prefix}-', 'prefix')
            total = 0; first = 0; middle = 0; last = 0
            for la, p, l, pos, w in rows:
                if la != lang: continue
                if not w.startswith(prefix): continue
                total += 1
                mx = line_max[(la, p, l)]
                if pos == 1: first += 1
                elif pos == mx: last += 1
                else: middle += 1
            if total > 0:
                results[key] = (total, first, middle, last)
                
        for suffix in suffixes:
            key = (lang, f'-{suffix}', 'suffix')
            total = 0; first = 0; middle = 0; last = 0
            for la, p, l, pos, w in rows:
                if la != lang: continue
                if not w.endswith(suffix): continue
                total += 1
                mx = line_max[(la, p, l)]
                if pos == 1: first += 1
                elif pos == mx: last += 1
                else: middle += 1
            if total > 0:
                results[key] = (total, first, middle, last)
    
    print("================================================================")
    print(" Deep Dive: Positional Heatmap of ALL Major Affixes (A vs B) ")
    print("================================================================")
    print()
    
    # Print as a comparative table: for each affix, show A and B side by side
    all_affixes = [f'{p}-' for p in prefixes] + [f'-{s}' for s in suffixes]
    
    print(f"{'Affix':<10} | {'Lang':>4} | {'Total':>6} | {'First%':>7} | {'Middle%':>8} | {'Last%':>7} | {'Delta_First':>12} | {'Delta_Last':>11}")
    print("-" * 90)
    
    for affix in all_affixes:
        affix_type = 'prefix' if affix.endswith('-') else 'suffix'
        key_A = ('A', affix, affix_type)
        key_B = ('B', affix, affix_type)
        
        if key_A not in results and key_B not in results: continue
        
        t_A, f_A, m_A, l_A = results.get(key_A, (0, 0, 0, 0))
        t_B, f_B, m_B, l_B = results.get(key_B, (0, 0, 0, 0))
        
        pf_A = (f_A / t_A * 100) if t_A else 0
        pm_A = (m_A / t_A * 100) if t_A else 0
        pl_A = (l_A / t_A * 100) if t_A else 0
        
        pf_B = (f_B / t_B * 100) if t_B else 0
        pm_B = (m_B / t_B * 100) if t_B else 0
        pl_B = (l_B / t_B * 100) if t_B else 0
        
        delta_first = pf_A - pf_B
        delta_last = pl_A - pl_B
        
        print(f"{affix:<10} | {'A':>4} | {t_A:>6} | {pf_A:>6.1f}% | {pm_A:>7.1f}% | {pl_A:>6.1f}% |             |")
        print(f"{'':10} | {'B':>4} | {t_B:>6} | {pf_B:>6.1f}% | {pm_B:>7.1f}% | {pl_B:>6.1f}% | {delta_first:>+11.1f}% | {delta_last:>+10.1f}%")
        print("-" * 90)
    
    print()
    print("Delta = (A% - B%). Positive = A uses it more in that position. Negative = B uses it more.")
    print("Large deltas (>10%) indicate fundamentally different positional formatting rules between dialects.")

if __name__ == "__main__":
    with open(r'positional_heatmap.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        main()
