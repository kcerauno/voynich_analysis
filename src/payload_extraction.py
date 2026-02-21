import sqlite3
import re
import math
from collections import Counter, defaultdict
import sys

# ===== Container elements identified in all previous analyses =====

# Tier 1: High-confidence container (formatting/structural)
LINE_END_MARKERS = {'am', 'om', 'aim'}  # 74-68% line-end
LINE_START_MARKERS = {'oees', 'okeos'}  # 78-43% line-start

# Tier 2: High-frequency padding prefixes (context-dependent, interchangeable across dialects)
CONTAINER_PREFIXES = ['qo', 'ch', 'sh', 'ok', 'ot', 'qot', 'qok']

# Tier 3: High-frequency padding suffixes
CONTAINER_SUFFIXES = ['dy', 'in', 'ey', 'am', 'om']

# Tier 4: Pure grammatical particles (from positional analysis: 86-91% mid-line, universal across categories)  
GRAMMAR_PARTICLES = {'al', 'ar', 'or', 's'}

def strip_container(word):
    """Multi-layer container stripping to extract payload core."""
    
    # Layer 0: If the word IS a known container element, payload = empty
    if word in LINE_END_MARKERS or word in LINE_START_MARKERS or word in GRAMMAR_PARTICLES:
        return '', 'PURE_CONTAINER'
    
    original = word
    
    # Layer 1: Strip prefix (longest match first)
    prefix_stripped = ''
    for p in sorted(CONTAINER_PREFIXES, key=len, reverse=True):
        if word.startswith(p) and len(word) > len(p):
            prefix_stripped = p
            word = word[len(p):]
            break
    
    # Layer 2: Strip suffix (longest match first)
    suffix_stripped = ''
    for s in sorted(CONTAINER_SUFFIXES, key=len, reverse=True):
        if word.endswith(s) and len(word) > len(s):
            suffix_stripped = s
            word = word[:-len(s)]
            break
    
    if len(word) == 0:
        return '', 'ANNIHILATED'
    
    return word, 'PAYLOAD'

def shannon_entropy(items):
    if not items: return 0
    counts = Counter(items)
    total = len(items)
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
    
    cursor.execute("""
    SELECT page, line_number, word_position, word, category, language
    FROM words_enriched 
    WHERE word IS NOT NULL AND word != ''
    ORDER BY page, line_number, word_position
    """)
    rows = cursor.fetchall()
    conn.close()
    
    print("================================================================")
    print(" CONTAINER-PAYLOAD DECOMPOSITION OF THE VOYNICH MANUSCRIPT ")
    print("================================================================")
    
    original_words = []
    payload_cores = []
    classifications = Counter()
    annihilated_words = []
    container_budget = Counter()
    payload_by_category = defaultdict(list)
    payload_by_language = defaultdict(list)
    
    for p, l, pos, w, cat, lang in rows:
        w_clean = re.sub(r'[^a-zA-Z]', '', w)
        if len(w_clean) < 1: continue
        
        original_words.append(w_clean)
        core, classification = strip_container(w_clean)
        classifications[classification] += 1
        
        if classification == 'PURE_CONTAINER':
            container_budget['pure_marker'] += 1
        elif classification == 'ANNIHILATED':
            annihilated_words.append(w_clean)
            container_budget['annihilated'] += 1
        else:
            payload_cores.append(core)
            if cat: payload_by_category[cat].append(core)
            if lang: payload_by_language[lang].append(core)
    
    total = len(original_words)
    
    print(f"\n--- 1. Decomposition Statistics ---")
    print(f"Total words in manuscript: {total}")
    print(f"  PAYLOAD (Core extracted):  {classifications['PAYLOAD']:>6} ({classifications['PAYLOAD']/total*100:.1f}%)")
    print(f"  PURE CONTAINER (markers):  {classifications['PURE_CONTAINER']:>6} ({classifications['PURE_CONTAINER']/total*100:.1f}%)")
    print(f"  ANNIHILATED (all padding): {classifications['ANNIHILATED']:>6} ({classifications['ANNIHILATED']/total*100:.1f}%)")
    
    # Character-level compression
    original_chars = sum(len(w) for w in original_words)
    payload_chars = sum(len(c) for c in payload_cores)
    
    print(f"\n--- 2. Compression Ratio ---")
    print(f"Original total characters: {original_chars}")
    print(f"Payload total characters:  {payload_chars}")
    print(f"Compression ratio: {payload_chars/original_chars*100:.1f}% (payload is {payload_chars/original_chars*100:.1f}% of original)")
    print(f"Container overhead: {(1-payload_chars/original_chars)*100:.1f}%")
    
    # Information content comparison
    orig_entropy = shannon_entropy(original_words)
    payload_entropy = shannon_entropy(payload_cores)
    
    orig_char_entropy = shannon_entropy(list(''.join(original_words)))
    payload_char_entropy = shannon_entropy(list(''.join(payload_cores)))
    
    print(f"\n--- 3. Information Content (Shannon Entropy) ---")
    print(f"Original word-level entropy:  {orig_entropy:.2f} bits")
    print(f"Payload word-level entropy:   {payload_entropy:.2f} bits")
    print(f"Original char-level entropy:  {orig_char_entropy:.2f} bits")
    print(f"Payload char-level entropy:   {payload_char_entropy:.2f} bits")
    
    orig_info = orig_entropy * total
    payload_info = payload_entropy * len(payload_cores)
    print(f"\nTotal information (word-level):")
    print(f"  Original: {orig_entropy:.2f} * {total} = {orig_info:.0f} bits")
    print(f"  Payload:  {payload_entropy:.2f} * {len(payload_cores)} = {payload_info:.0f} bits")
    print(f"  Ratio: {payload_info/orig_info*100:.1f}% of original information retained in payload")
    
    # Top payload cores
    payload_counter = Counter(payload_cores)
    
    print(f"\n--- 4. Top 30 Payload Cores (The Hidden Message Vocabulary) ---")
    print(f"Unique payload types: {len(payload_counter)} (vs {len(Counter(original_words))} original)")
    
    for i, (core, cnt) in enumerate(payload_counter.most_common(30)):
        bar = '#' * min(cnt // 5, 50)
        print(f"  {i+1:>2}. {core:<8} {cnt:>5} {bar}")
    
    # Payload core length distribution
    print(f"\n--- 5. Payload Core Length Distribution ---")
    len_dist = Counter(len(c) for c in payload_cores)
    for length in sorted(len_dist.keys()):
        pct = len_dist[length] / len(payload_cores) * 100
        bar = '#' * int(pct)
        print(f"  {length} chars: {len_dist[length]:>5} ({pct:>5.1f}%) {bar}")
    
    # Payload per category
    print(f"\n--- 6. Payload Entropy by Category ---")
    for cat in ['herbal', 'textonly', 'biological', 'pharmaceutical', 'cosmological', 'astronomical', 'astrology']:
        cores = payload_by_category.get(cat, [])
        if not cores: continue
        ent = shannon_entropy(cores)
        unique = len(set(cores))
        print(f"  {cat:<15}: {len(cores):>5} cores, {unique:>4} unique, H={ent:.2f}")
    
    # Payload per dialect
    print(f"\n--- 7. Payload: Language A vs B ---")
    for lang in ['A', 'B']:
        cores = payload_by_language.get(lang, [])
        if not cores: continue
        ent = shannon_entropy(cores)
        top = Counter(cores).most_common(5)
        top_str = ", ".join(f"{w}({c})" for w, c in top)
        print(f"  Language {lang}: {len(cores)} cores, H={ent:.2f}")
        print(f"    Top: {top_str}")
    
    # Annihilated words (100% container)
    print(f"\n--- 8. Most Common ANNIHILATED Words (100% Container) ---")
    ann_counter = Counter(annihilated_words)
    for w, cnt in ann_counter.most_common(15):
        print(f"  {w:<10}: {cnt}")
    
    # Extract first 100 words of payload as a "decrypted" stream
    print(f"\n--- 9. First 200 Payload Cores (The 'Decrypted' Stream) ---")
    stream = ' '.join(payload_cores[:200])
    print(stream)

if __name__ == "__main__":
    with open(r'payload_extraction.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        main()
