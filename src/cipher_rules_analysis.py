import sqlite3
import re
from collections import defaultdict, Counter
import sys
from difflib import SequenceMatcher

try:
    from gensim.models import Word2Vec
    import numpy as np
    from scipy.linalg import orthogonal_procrustes
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

def get_closest(word, model_source, model_target, R, mean_source, mean_target):
    if word not in model_source.wv: return None
    vec_s = model_source.wv[word]
    vec_s_aligned = ((vec_s - mean_source) @ R) + mean_target
    
    target_vocab = model_target.wv.index_to_key
    target_vectors = model_target.wv.vectors
    
    norm_s = np.linalg.norm(vec_s_aligned)
    if norm_s == 0: return None
    
    norms_target = np.linalg.norm(target_vectors, axis=1)
    norms_target[norms_target == 0] = 1e-10
    
    dot_products = np.dot(target_vectors, vec_s_aligned)
    sims = dot_products / (norms_target * norm_s)
    
    best_idx = np.argmax(sims)
    return target_vocab[best_idx], sims[best_idx]

def extract_diff_rules(wA, wB):
    # Use SequenceMatcher to find the longest matching core
    sm = SequenceMatcher(None, wA, wB)
    match = sm.find_longest_match(0, len(wA), 0, len(wB))
    
    core = wA[match.a: match.a + match.size] if match.size > 0 else ""
    
    if len(core) == 0:
        return "Complete Transformation", ""
        
    pref_A = wA[:match.a]
    suff_A = wA[match.a + match.size:]
    
    pref_B = wB[:match.b]
    suff_B = wB[match.b + match.size:]
    
    rule = ""
    if pref_A != pref_B:
        pA = pref_A if pref_A else "[None]"
        pB = pref_B if pref_B else "[None]"
        rule += f"Prefix: {pA} -> {pB} | "
    if suff_A != suff_B:
        sA = suff_A if suff_A else "[None]"
        sB = suff_B if suff_B else "[None]"
        rule += f"Suffix: {sA} -> {sB}"
        
    return rule.strip(' | ') if rule else "Identical", core

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
    
    R_AtoB, mean_A, mean_B = align_spaces(model_A, model_B, common_words)
    
    # We will test the top 200 words from A
    top_A = [w for w, c in counts_A.most_common(300) if w in vocab_A]
    
    rules_counter = Counter()
    core_preservation = 0
    total_matches = 0
    
    print("==================================================")
    print(" Cipher Transformation Rule Analysis (A -> B) ")
    print("==================================================")
    
    print(f"\nAnalyzing transformation vectors for Top Words...\n")
    
    for wA in top_A:
        res = get_closest(wA, model_A, model_B, R_AtoB, mean_A, mean_B)
        if not res: continue
        wB, sim = res
        
        # Only analyze confident semantic alignments
        if sim < 0.85: continue
        
        rule, core = extract_diff_rules(wA, wB)
        
        if rule != "Identical" and rule != "Complete Transformation":
            rules_counter[rule] += 1
            total_matches += 1
            if len(core) >= 2:
                core_preservation += 1
                
        if total_matches < 15: # Print first few examples
            print(f"Alignment: {wA:<10} -> {wB:<10} (Sim: {sim:.2f})")
            print(f"  Shared Core: '{core}'")
            print(f"  Rule: {rule}\n")
            
    print("--------------------------------------------------")
    print(" Dominant Cipher Modification Rules (Lang A -> Lang B)")
    print("--------------------------------------------------")
    for r, c in rules_counter.most_common(15):
        print(f"  {r:<40} : {c} occurrences")
        
    print(f"\nOut of {total_matches} high-confidence transformations:")
    print(f"{core_preservation} times ({(core_preservation/total_matches)*100:.1f}%), the 'Core' stem (2+ chars) was completely preserved.")
    print("\nConclusion on Original Form:")
    print("If the 'Core' remains mathematically identical while the affixes swap predictably, ")
    print("then the 'Core' IS the true underlying (unencrypted) information content, ")
    print("and the shifting affixes are context-dependent Dummy/Padding algorithms.")

if __name__ == "__main__":
    with open(r'cipher_rules_analysis.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        main()
