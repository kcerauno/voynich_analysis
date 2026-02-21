import sqlite3
import re
from collections import Counter, defaultdict
import sys

try:
    from gensim.models import Word2Vec
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
except ImportError:
    print("Error: gensim, numpy, sklearn required.")
    sys.exit(1)

# Known high-frequency affixes (from our earlier analysis)
COMMON_PREFIXES = ['qo', 'ch', 'sh', 'ok', 'ot', 'da', 'qot', 'qok']
COMMON_SUFFIXES = ['dy', 'in', 'ey', 'ol', 'y', 'n', 'l', 'r', 'am']

def has_known_affix(w):
    for p in COMMON_PREFIXES:
        if w.startswith(p) and len(w) > len(p): return True
    for s in COMMON_SUFFIXES:
        if w.endswith(s) and len(w) > len(s): return True
    return False

def main():
    db_path = r'data\voynich.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT word FROM words_enriched 
    WHERE word IS NOT NULL AND word != ''
    """)
    all_words_raw = [re.sub(r'[^a-zA-Z]', '', r[0]) for r in cursor.fetchall()]
    all_words_raw = [w for w in all_words_raw if len(w) >= 2]
    
    word_counts = Counter(all_words_raw)
    
    # Build sentences for Word2Vec
    cursor.execute("""
    SELECT page, line_number, word_position, word 
    FROM words_enriched 
    WHERE word IS NOT NULL AND word != ''
    ORDER BY page, line_number, word_position
    """)
    rows = cursor.fetchall()
    conn.close()
    
    sentences = defaultdict(list)
    for p, l, pos, w in rows:
        w_clean = re.sub(r'[^a-zA-Z]', '', w)
        if len(w_clean) >= 2:
            sentences[(p, l)].append(w_clean)
    sent_list = list(sentences.values())
    
    print("==================================================")
    print(" Approach 3: W2V Clustering of Short Independent Words ")
    print("==================================================")
    
    # Train Word2Vec on full corpus
    model = Word2Vec(sentences=sent_list, vector_size=50, window=5, min_count=3, workers=4, epochs=30)
    
    # Find short (2-4 char) words that lack common affixes and appear >= 3 times
    short_independent = []
    for w, cnt in word_counts.items():
        if 2 <= len(w) <= 4 and cnt >= 3 and not has_known_affix(w) and w in model.wv:
            short_independent.append(w)
    
    print(f"Short (2-4 char), affix-free, frequent (>=3) words in W2V: {len(short_independent)}")
    
    if len(short_independent) < 5:
        print("Not enough short independent words for clustering.")
        return
    
    # Get vectors
    vectors = np.array([model.wv[w] for w in short_independent])
    
    # KMeans clustering
    n_clusters = min(5, len(short_independent) // 2)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(vectors)
    
    # PCA for 2D visualization coordinates
    pca = PCA(n_components=2)
    coords = pca.fit_transform(vectors)
    
    # Group by cluster
    clusters = defaultdict(list)
    for i, w in enumerate(short_independent):
        clusters[labels[i]].append((w, word_counts[w], coords[i][0], coords[i][1]))
    
    # Also check which of our astronomy candidates are in the model
    astro_candidates = ['oto', 'alar', 'alal', 'ypal', 'alos', 'ofor']
    
    print(f"\n--- Cluster Results ({n_clusters} clusters) ---")
    for cid in sorted(clusters.keys()):
        members = clusters[cid]
        members.sort(key=lambda x: x[1], reverse=True)
        print(f"\nCluster {cid} ({len(members)} words):")
        for w, cnt, x, y in members:
            astro_tag = " *** ASTRO CANDIDATE ***" if w in astro_candidates else ""
            print(f"  {w:<8} (freq: {cnt:>4}, PCA: {x:+.2f}, {y:+.2f}){astro_tag}")
    
    # Check if astro candidates cluster together
    astro_clusters = set()
    for w in astro_candidates:
        for cid, members in clusters.items():
            if w in [m[0] for m in members]:
                astro_clusters.add(cid)
                
    print(f"\n--- Astro candidate cluster IDs: {astro_clusters} ---")
    if len(astro_clusters) == 1:
        print(">>> ALL astronomical numeral candidates are in the SAME cluster!")
        print(">>> This strongly supports they form a coherent semantic group (e.g., numerals).")
    else:
        print(">>> Astronomical candidates are spread across clusters.")
        print(">>> They may not form a single semantic category, or the data is too sparse.")
    
    # Find nearest neighbors of 'oto' (our prime suspect)
    if 'oto' in model.wv:
        print(f"\n--- Nearest neighbors of 'oto' (prime numeral candidate) ---")
        neighbors = model.wv.most_similar('oto', topn=10)
        for w, sim in neighbors:
            astro_tag = " *** ASTRO ***" if w in astro_candidates else ""
            print(f"  {w:<12} (similarity: {sim:.3f}){astro_tag}")

if __name__ == "__main__":
    with open(r'numeral_clustering.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        main()
