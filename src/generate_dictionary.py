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
    print("Error: gensim, numpy, and scipy are required.")
    sys.exit(1)

def get_sentences_and_counts(cursor, lang):
    query = """
    SELECT page, line_number, word_position, word 
    FROM words_enriched 
    WHERE language = ? AND word IS NOT NULL AND word != ''
    ORDER BY page, line_number, word_position;
    """
    cursor.execute(query, (lang,))
    rows = cursor.fetchall()
    
    sentences = defaultdict(list)
    counts = Counter()
    for p, l, pos, w in rows:
        w_clean = re.sub(r'[^a-zA-Z]', '', w)
        if len(w_clean) > 0:
            sentences[(p, l)].append(w_clean)
            counts[w_clean] += 1
            
    return list(sentences.values()), counts

def align_spaces(model_A, model_B, common_words):
    vecs_A = np.array([model_A.wv[w] for w in common_words])
    vecs_B = np.array([model_B.wv[w] for w in common_words])
    
    mean_A = vecs_A.mean(axis=0)
    mean_B = vecs_B.mean(axis=0)
    
    vecs_A_centered = vecs_A - mean_A
    vecs_B_centered = vecs_B - mean_B
    
    R, scale = orthogonal_procrustes(vecs_A_centered, vecs_B_centered)
    return R, mean_A, mean_B

def get_closest_in_target(word_in_source, model_source, model_target, R, mean_source, mean_target, topn=3):
    if word_in_source not in model_source.wv:
        return []
        
    vec_s = model_source.wv[word_in_source]
    vec_s_aligned = ((vec_s - mean_source) @ R) + mean_target
    
    similarities = []
    # Optimization: calculate cosine against all target vectors vectorized
    target_vocab = model_target.wv.index_to_key
    target_vectors = model_target.wv.vectors
    
    # Cosine similarity = dot(A, B) / (norm(A) * norm(B))
    norm_s = np.linalg.norm(vec_s_aligned)
    if norm_s == 0: return []
    
    norms_target = np.linalg.norm(target_vectors, axis=1)
    # Avoid div by zero
    norms_target[norms_target == 0] = 1e-10
    
    dot_products = np.dot(target_vectors, vec_s_aligned)
    sims = dot_products / (norms_target * norm_s)
    
    # Get top indices
    top_indices = np.argsort(sims)[::-1][:topn]
    
    return [(target_vocab[i], sims[i]) for i in top_indices]

def main():
    db_path = r'data\voynich.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    sents_A, counts_A = get_sentences_and_counts(cursor, 'A')
    sents_B, counts_B = get_sentences_and_counts(cursor, 'B')
    conn.close()
    
    model_A = Word2Vec(sentences=sents_A, vector_size=100, window=5, min_count=5, workers=4, epochs=30)
    model_B = Word2Vec(sentences=sents_B, vector_size=100, window=5, min_count=5, workers=4, epochs=30)
    
    vocab_A = set(model_A.wv.index_to_key)
    vocab_B = set(model_B.wv.index_to_key)
    common_words = list(vocab_A.intersection(vocab_B))
    
    print("Aligning A -> B...")
    R_AtoB, mean_A, mean_B = align_spaces(model_A, model_B, common_words)
    
    print("Aligning B -> A...")
    R_BtoA, mean_B2, mean_A2 = align_spaces(model_B, model_A, common_words)
    
    top_A = [w for w, c in counts_A.most_common(120) if w in vocab_A][:100]
    top_B = [w for w, c in counts_B.most_common(120) if w in vocab_B][:100]
    
    md_output = [
        "# ヴォイニッチ手稿: Currier言語 A ⇔ B 翻訳辞書（Semantic Vector Mapping）",
        "",
        "この辞書は、Currier言語Aと言語BのWord2Vec意味ベクトル空間を直交プロクラステス分析で結合し、一方の言語で高頻出する単語（または形態素）が、もう一方の言語の「どの単語と全く同じ文脈・構文機能で使われているか」を数学的にマッピングしたものです。",
        "",
        "## 1. 言語A → 言語B 翻訳辞書 (Top 100語)",
        "| 言語A (Frequency) | 最も近い言語Bの単語 1 (類似度) | 翻訳候補 2 | 翻訳候補 3 |",
        "| :--- | :--- | :--- | :--- |"
    ]
    
    for w in top_A:
        closest = get_closest_in_target(w, model_A, model_B, R_AtoB, mean_A, mean_B, topn=3)
        if closest:
            c1 = f"`{closest[0][0]}` ({closest[0][1]:.2f})" if len(closest) > 0 else ""
            c2 = f"`{closest[1][0]}` ({closest[1][1]:.2f})" if len(closest) > 1 else ""
            c3 = f"`{closest[2][0]}` ({closest[2][1]:.2f})" if len(closest) > 2 else ""
            md_output.append(f"| **`{w}`** ({counts_A[w]}) | {c1} | {c2} | {c3} |")
            
    md_output.extend([
        "",
        "---",
        "",
        "## 2. 言語B → 言語A 翻訳辞書 (Top 100語)",
        "| 言語B (Frequency) | 最も近い言語Aの単語 1 (類似度) | 翻訳候補 2 | 翻訳候補 3 |",
        "| :--- | :--- | :--- | :--- |"
    ])
    
    for w in top_B:
        closest = get_closest_in_target(w, model_B, model_A, R_BtoA, mean_B2, mean_A2, topn=3)
        if closest:
            c1 = f"`{closest[0][0]}` ({closest[0][1]:.2f})" if len(closest) > 0 else ""
            c2 = f"`{closest[1][0]}` ({closest[1][1]:.2f})" if len(closest) > 1 else ""
            c3 = f"`{closest[2][0]}` ({closest[2][1]:.2f})" if len(closest) > 2 else ""
            md_output.append(f"| **`{w}`** ({counts_B[w]}) | {c1} | {c2} | {c3} |")
            
    with open(r'Currier_A_B_Dictionary.md', 'w', encoding='utf-8') as f:
        f.write("\n".join(md_output))
        
    print("Dictionary successfully generated.")

if __name__ == "__main__":
    main()
