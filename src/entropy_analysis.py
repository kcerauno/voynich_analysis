import sqlite3
import re
from collections import Counter, defaultdict
import math
import sys

def shannon_entropy(word_list):
    if not word_list: return 0
    counts = Counter(word_list)
    total = len(word_list)
    entropy = 0
    for c in counts.values():
        p = c / total
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy

def main():
    db_path = r'data\voynich.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("==============================================================")
    print(" 7. Information Entropy Change Point Analysis ")
    print("==============================================================")
    
    cursor.execute("""
    SELECT page, line_number, word_position, word, category
    FROM words_enriched 
    WHERE word IS NOT NULL AND word != ''
    ORDER BY page, line_number, word_position
    """)
    rows = cursor.fetchall()
    
    # Build ordered word stream with page markers
    word_stream = []
    page_boundaries = {}  # index -> (page, category)
    current_page = None
    
    for p, l, pos, w, cat in rows:
        w_clean = re.sub(r'[^a-zA-Z]', '', w)
        if len(w_clean) < 2: continue
        
        if p != current_page:
            page_boundaries[len(word_stream)] = (p, cat)
            current_page = p
        
        word_stream.append(w_clean)
    
    print(f"Total word stream length: {len(word_stream)}")
    print(f"Total page boundaries: {len(page_boundaries)}")
    
    # Sliding window entropy calculation
    WINDOW = 50  # 50 words per window
    STEP = 25    # Slide by 25 words
    
    entropies = []
    positions = []
    
    for i in range(0, len(word_stream) - WINDOW, STEP):
        window = word_stream[i:i+WINDOW]
        ent = shannon_entropy(window)
        entropies.append(ent)
        positions.append(i)
    
    # Find change points (large jumps in entropy)
    print(f"\n--- Entropy Change Points (Window={WINDOW}, Step={STEP}) ---")
    print("Large jumps indicate topic/section boundaries.\n")
    
    changes = []
    for i in range(1, len(entropies)):
        delta = abs(entropies[i] - entropies[i-1])
        changes.append((i, positions[i], delta, entropies[i-1], entropies[i]))
    
    changes.sort(key=lambda x: x[2], reverse=True)
    
    print(f"{'Rank':>4} | {'WordPos':>8} | {'Delta':>6} | {'Before':>7} | {'After':>7} | {'Page':>10} | {'Category'}")
    print("-" * 80)
    
    for rank, (idx, wpos, delta, before, after, ) in enumerate(changes[:20]):
        # Find which page this position falls in
        page = "?"
        cat = "?"
        for bp in sorted(page_boundaries.keys(), reverse=True):
            if wpos >= bp:
                page, cat = page_boundaries[bp]
                break
        
        # Find what words are at the boundary
        boundary_words = word_stream[max(0,wpos-3):wpos+3]
        bw_str = " ".join(boundary_words)
        
        print(f"{rank+1:>4} | {wpos:>8} | {delta:>5.2f} | {before:>6.2f} | {after:>6.2f} | {page:>10} | {cat}")
    
    # Identify words that appear ONLY at entropy change points
    print(f"\n--- Words Concentrated Near Entropy Spikes ---")
    print("(Words that appear primarily at topic boundaries = chapter titles/section markers)")
    
    # Get top 10 change points
    spike_positions = set()
    for _, wpos, delta, _, _ in changes[:10]:
        for j in range(max(0, wpos-5), min(len(word_stream), wpos+5)):
            spike_positions.add(j)
    
    spike_words = Counter()
    for pos in spike_positions:
        spike_words[word_stream[pos]] += 1
    
    # Compare with overall frequency
    overall = Counter(word_stream)
    
    print(f"\n{'Word':<14} | {'At Spikes':>9} | {'Total':>6} | {'Spike%':>7}")
    print("-" * 45)
    
    for w, spike_cnt in spike_words.most_common(20):
        total_cnt = overall[w]
        spike_pct = (spike_cnt / total_cnt * 100) if total_cnt else 0
        print(f"{w:<14} | {spike_cnt:>9} | {total_cnt:>6} | {spike_pct:>6.1f}%")
    
    # Per-page entropy summary
    print(f"\n--- Per-Page Entropy Summary ---")
    page_entropies = []
    
    bp_list = sorted(page_boundaries.keys())
    for i, bp in enumerate(bp_list):
        next_bp = bp_list[i+1] if i+1 < len(bp_list) else len(word_stream)
        page_words = word_stream[bp:next_bp]
        if len(page_words) < 5: continue
        ent = shannon_entropy(page_words)
        page, cat = page_boundaries[bp]
        page_entropies.append((page, cat, ent, len(page_words)))
    
    # Sort by entropy to find lowest (most repetitive) and highest (most diverse)
    page_entropies.sort(key=lambda x: x[2])
    
    print("\nMost REPETITIVE pages (lowest entropy):")
    for p, cat, ent, n in page_entropies[:10]:
        print(f"  {p:<10} [{cat:<15}] Entropy: {ent:.2f} ({n} words)")
    
    print("\nMost DIVERSE pages (highest entropy):")
    for p, cat, ent, n in page_entropies[-10:]:
        print(f"  {p:<10} [{cat:<15}] Entropy: {ent:.2f} ({n} words)")
    
    conn.close()

if __name__ == "__main__":
    with open(r'entropy_analysis.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        main()
