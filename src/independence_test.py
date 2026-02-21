import sqlite3
import re
import math
from collections import Counter, defaultdict
import sys

CONTAINER_PREFIXES = ['qo', 'ch', 'sh', 'ok', 'ot', 'qot', 'qok']
CONTAINER_SUFFIXES = ['dy', 'in', 'ey', 'am', 'om']

def decompose(word):
    """Returns (prefix, core, suffix) tuple."""
    prefix = ''
    suffix = ''
    
    for p in sorted(CONTAINER_PREFIXES, key=len, reverse=True):
        if word.startswith(p) and len(word) > len(p):
            prefix = p
            word = word[len(p):]
            break
    
    for s in sorted(CONTAINER_SUFFIXES, key=len, reverse=True):
        if word.endswith(s) and len(word) > len(s):
            suffix = s
            word = word[:-len(s)]
            break
    
    return prefix or '[NONE]', word, suffix or '[NONE]'

def shannon_entropy(items):
    if not items: return 0
    counts = Counter(items)
    total = len(items)
    return -sum((c/total) * math.log2(c/total) for c in counts.values() if c > 0)

def conditional_entropy(X, Y):
    """H(Y|X) = entropy of Y given X. Lower = more predictable."""
    joint = Counter(zip(X, Y))
    x_counts = Counter(X)
    total = len(X)
    
    h = 0
    for (x, y), xy_count in joint.items():
        p_xy = xy_count / total
        p_x = x_counts[x] / total
        h -= p_xy * math.log2(p_xy / p_x)
    return h

def mutual_information(X, Y):
    """I(X;Y) = H(Y) - H(Y|X). Higher = more dependent."""
    h_y = shannon_entropy(Y)
    h_y_given_x = conditional_entropy(X, Y)
    return h_y - h_y_given_x

def main():
    db_path = r'data\voynich.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT word FROM words_enriched 
    WHERE word IS NOT NULL AND word != ''
    ORDER BY page, line_number, word_position
    """)
    
    prefixes = []
    cores = []
    suffixes = []
    containers = []  # prefix+suffix combined
    
    for (w,) in cursor.fetchall():
        w_clean = re.sub(r'[^a-zA-Z]', '', w)
        if len(w_clean) < 2: continue
        
        p, c, s = decompose(w_clean)
        prefixes.append(p)
        cores.append(c)
        suffixes.append(s)
        containers.append(f"{p}+{s}")
    
    conn.close()
    
    print("================================================================")
    print(" CONTAINER-PAYLOAD INDEPENDENCE TEST ")
    print("================================================================")
    print(f"Total decomposed words: {len(cores)}")
    
    # 1. Entropy of each component
    h_prefix = shannon_entropy(prefixes)
    h_core = shannon_entropy(cores)
    h_suffix = shannon_entropy(suffixes)
    h_container = shannon_entropy(containers)
    
    print(f"\n--- 1. Component Entropies ---")
    print(f"  H(Prefix):    {h_prefix:.2f} bits")
    print(f"  H(Core):      {h_core:.2f} bits")
    print(f"  H(Suffix):    {h_suffix:.2f} bits")
    print(f"  H(Container): {h_container:.2f} bits [prefix+suffix combined]")
    
    # 2. Conditional entropies
    h_suffix_given_prefix = conditional_entropy(prefixes, suffixes)
    h_core_given_prefix = conditional_entropy(prefixes, cores)
    h_core_given_suffix = conditional_entropy(suffixes, cores)
    h_core_given_container = conditional_entropy(containers, cores)
    h_prefix_given_core = conditional_entropy(cores, prefixes)
    h_suffix_given_core = conditional_entropy(cores, suffixes)
    h_container_given_core = conditional_entropy(cores, containers)
    
    print(f"\n--- 2. Conditional Entropies ---")
    print(f"  H(Core|Prefix):     {h_core_given_prefix:.2f} (vs H(Core)={h_core:.2f})")
    print(f"  H(Core|Suffix):     {h_core_given_suffix:.2f} (vs H(Core)={h_core:.2f})")
    print(f"  H(Core|Container):  {h_core_given_container:.2f} (vs H(Core)={h_core:.2f})")
    print(f"  H(Prefix|Core):     {h_prefix_given_core:.2f} (vs H(Prefix)={h_prefix:.2f})")
    print(f"  H(Suffix|Core):     {h_suffix_given_core:.2f} (vs H(Suffix)={h_suffix:.2f})")
    print(f"  H(Container|Core):  {h_container_given_core:.2f} (vs H(Container)={h_container:.2f})")
    print(f"  H(Suffix|Prefix):   {h_suffix_given_prefix:.2f} (vs H(Suffix)={h_suffix:.2f})")
    
    # 3. Mutual Information
    mi_core_prefix = mutual_information(prefixes, cores)
    mi_core_suffix = mutual_information(suffixes, cores)
    mi_core_container = mutual_information(containers, cores)
    mi_prefix_suffix = mutual_information(prefixes, suffixes)
    
    print(f"\n--- 3. Mutual Information (Dependency Strength) ---")
    print(f"  I(Core; Prefix):    {mi_core_prefix:.3f} bits")
    print(f"  I(Core; Suffix):    {mi_core_suffix:.3f} bits")
    print(f"  I(Core; Container): {mi_core_container:.3f} bits")
    print(f"  I(Prefix; Suffix):  {mi_prefix_suffix:.3f} bits")
    
    # Normalized MI
    nmi_core_prefix = mi_core_prefix / min(h_core, h_prefix) if min(h_core, h_prefix) > 0 else 0
    nmi_core_suffix = mi_core_suffix / min(h_core, h_suffix) if min(h_core, h_suffix) > 0 else 0
    nmi_core_container = mi_core_container / min(h_core, h_container) if min(h_core, h_container) > 0 else 0
    nmi_prefix_suffix = mi_prefix_suffix / min(h_prefix, h_suffix) if min(h_prefix, h_suffix) > 0 else 0
    
    print(f"\n  Normalized MI (0=independent, 1=fully determined):")
    print(f"  NMI(Core; Prefix):    {nmi_core_prefix:.4f}")
    print(f"  NMI(Core; Suffix):    {nmi_core_suffix:.4f}")
    print(f"  NMI(Core; Container): {nmi_core_container:.4f}")
    print(f"  NMI(Prefix; Suffix):  {nmi_prefix_suffix:.4f}")
    
    # 4. Top core-container associations
    print(f"\n--- 4. Top Core-Container Associations ---")
    print("(Which cores are most 'bound' to specific containers?)")
    
    core_container_pairs = list(zip(cores, containers))
    core_top = Counter(cores).most_common(15)
    
    for core, total_cnt in core_top:
        containers_for_core = [ct for c, ct in core_container_pairs if c == core]
        ct_dist = Counter(containers_for_core)
        top_ct = ct_dist.most_common(3)
        
        # Calculate how predictable the container is for this core
        h_ct_for_core = shannon_entropy(containers_for_core)
        
        top_str = " | ".join(f"{ct}({cnt},{cnt/total_cnt*100:.0f}%)" for ct, cnt in top_ct)
        print(f"  Core '{core}' (n={total_cnt}, H_container={h_ct_for_core:.2f}): {top_str}")
    
    # 5. Does knowing the PREVIOUS word's container predict the CURRENT word's container?
    print(f"\n--- 5. Sequential Container Dependency ---")
    prev_containers = containers[:-1]
    curr_containers = containers[1:]
    
    h_curr = shannon_entropy(curr_containers)
    h_curr_given_prev = conditional_entropy(prev_containers, curr_containers)
    mi_seq = h_curr - h_curr_given_prev
    
    print(f"  H(CurrentContainer):                {h_curr:.2f} bits")
    print(f"  H(CurrentContainer|PrevContainer):   {h_curr_given_prev:.2f} bits")
    print(f"  MI(PrevContainer; CurrentContainer):  {mi_seq:.3f} bits")
    print(f"  Reduction: {(1 - h_curr_given_prev/h_curr)*100:.1f}%")

if __name__ == "__main__":
    with open(r'independence_test.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        main()
