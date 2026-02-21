import sqlite3
import re
from collections import defaultdict, Counter
import sys

try:
    from gensim.models import Word2Vec
    import numpy as np
    from scipy.linalg import orthogonal_procrustes
    from scipy.spatial.distance import cosine
except ImportError:
    print("Error: gensim, numpy, and scipy are required. Please run: pip install gensim scipy numpy")
    sys.exit(1)

def get_sentences(cursor, lang):
    query = """
    SELECT page, line_number, word_position, word 
    FROM words_enriched 
    WHERE language = ? AND word IS NOT NULL AND word != ''
    ORDER BY page, line_number, word_position;
    """
    cursor.execute(query, (lang,))
    rows = cursor.fetchall()
    
    sentences = defaultdict(list)
    for p, l, pos, w in rows:
        w_clean = re.sub(r'[^a-zA-Z]', '', w)
        if len(w_clean) > 0:
            sentences[(p, l)].append(w_clean)
            
    return list(sentences.values())

def align_spaces(model_A, model_B, common_words):
    # Extract vectors for the intersection vocabulary
    vecs_A = np.array([model_A.wv[w] for w in common_words])
    vecs_B = np.array([model_B.wv[w] for w in common_words])
    
    # Needs to be mean-centered before procrustes? 
    # Technically orthogonal_procrustes expects centered data for best semantic mapping.
    mean_A = vecs_A.mean(axis=0)
    mean_B = vecs_B.mean(axis=0)
    
    vecs_A_centered = vecs_A - mean_A
    vecs_B_centered = vecs_B - mean_B
    
    # Calculate transformation matrix R to map A onto B
    # vecs_A_centered @ R ≈ vecs_B_centered
    R, scale = orthogonal_procrustes(vecs_A_centered, vecs_B_centered)
    
    return R, mean_A, mean_B

def get_closest_in_B(word_in_A, model_A, model_B, R, mean_A, mean_B, topn=5):
    if word_in_A not in model_A.wv:
        return []
    
    # Get vector in A
    vec_a = model_A.wv[word_in_A]
    
    # Transform to B's space
    vec_a_aligned = ((vec_a - mean_A) @ R) + mean_B
    
    # Calculate cosine similarity against all words in B
    similarities = []
    for w_b in model_B.wv.index_to_key:
        vec_b = model_B.wv[w_b]
        # Cosine distance returns 0 for identical, 2 for opposite. Sim = 1 - dist
        sim = 1 - cosine(vec_a_aligned, vec_b)
        similarities.append((w_b, sim))
        
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:topn]

def main():
    db_path = r'data\voynich.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("==================================================")
    print(" 3. Word2Vec Dialect Vector Space Alignment ")
    print("==================================================")
    
    sents_A = get_sentences(cursor, 'A')
    sents_B = get_sentences(cursor, 'B')
    conn.close()
    
    print(f"Loaded Language A: {len(sents_A)} sentences (lines)")
    print(f"Loaded Language B: {len(sents_B)} sentences (lines)")
    
    # Train extremely aggressive models given the small data
    # window=5, min_count=5
    # Negative sampling, larger epochs since data is small
    print("Training Model A...")
    model_A = Word2Vec(sentences=sents_A, vector_size=100, window=5, min_count=5, workers=4, epochs=30)
    
    print("Training Model B...")
    model_B = Word2Vec(sentences=sents_B, vector_size=100, window=5, min_count=5, workers=4, epochs=30)
    
    vocab_A = set(model_A.wv.index_to_key)
    vocab_B = set(model_B.wv.index_to_key)
    
    common_words = list(vocab_A.intersection(vocab_B))
    print(f"\nVocabulary Intersection (words appearing >=5 times in BOTH): {len(common_words)} words")
    
    if len(common_words) < 10:
        print("Not enough common vocabulary to perform Procrustes alignment.")
        return
        
    print("Aligning Vector Spaces (Orthogonal Procrustes mapping A -> B)...")
    R, mean_A, mean_B = align_spaces(model_A, model_B, common_words)
    
    print("\n--- Semantic Shifts: Translating Lang A markers into Lang B ---")
    print("If Language A's 'ch-' perfectly maps to Language B's 'qo-', we will see it here.")
    
    # Test typical Language A markers
    targets_A = ['chol', 'daiin', 'shedy', 'chey', 'ar', 'ol', 'chedy']
    
    for word in targets_A:
        if word in vocab_A:
            closest = get_closest_in_B(word, model_A, model_B, R, mean_A, mean_B, topn=3)
            print(f"\nLanguage A word: [{word}]")
            print("  Closest semantic equivalents in Language B:")
            for w_b, sim in closest:
                print(f"    -> {w_b:<10} (Similarity: {sim:.3f})")

    # What about Language B markers translated to A?
    # We can inverse the translation. B -> A
    print("\n--- Semantic Shifts: Translating Lang B markers into Lang A ---")
    R_inv, mB, mA = align_spaces(model_B, model_A, common_words)
    targets_B = ['qo', 'qokedy', 'qokeedy', 'dy', 'ody', 'qotchy']
    
    for word in targets_B:
        if word in vocab_B:
            closest = get_closest_in_B(word, model_B, model_A, R_inv, mB, mA, topn=3)
            print(f"\nLanguage B word: [{word}]")
            print("  Closest semantic equivalents in Language A:")
            for w_a, sim in closest:
                print(f"    -> {w_a:<10} (Similarity: {sim:.3f})")

if __name__ == "__main__":
    with open(r'w2v_dialect_alignment.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        main()
