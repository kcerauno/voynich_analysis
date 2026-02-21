import sqlite3
import re
from collections import defaultdict, Counter
import sys

def main():
    db_path = r'data\voynich.db'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Query words and their metadata, excluding nulls and empties
    query = """
    SELECT word, category, language, scribe 
    FROM words_enriched 
    WHERE word IS NOT NULL AND word != '';
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    # Data structures to hold cleaned words grouped by metadata
    # Format: dict[group_name] = [list of cleaned words]
    by_category = defaultdict(list)
    by_language = defaultdict(list)
    by_scribe = defaultdict(list)
    
    for word, cat, lang, scribe in rows:
        # Clean word (keep only alphabets)
        w = re.sub(r'[^a-zA-Z]', '', word)
        if not w:
            continue
            
        # Group by category
        if cat:
            cat_clean = cat.strip()
            if cat_clean:
                by_category[cat_clean].append(w)
                
        # Group by language
        if lang:
            lang_clean = lang.strip()
            if lang_clean:
                by_language[lang_clean].append(w)
                
        # Group by scribe
        if scribe:
            scribe_clean = scribe.strip()
            if scribe_clean:
                by_scribe[scribe_clean].append(w)

    def analyze_group(group_dict, group_type, n=2, top_k=5):
        print(f"\n{'='*50}")
        print(f" Analysis by {group_type.upper()} (Prefix/Suffix Length: {n})")
        print(f"{'='*50}")
        
        # Sort groups by size (descending) to show major ones first
        sorted_groups = sorted(group_dict.items(), key=lambda x: len(x[1]), reverse=True)
        
        for name, words in sorted_groups:
            total = len(words)
            if total < 100:
                continue # Skip very small groups for statistical noise reduction
                
            prefixes = Counter()
            suffixes = Counter()
            
            for w in words:
                if len(w) > n:
                    prefixes[w[:n]] += 1
                    suffixes[w[-n:]] += 1
                    
            print(f"\n--- {group_type}: '{name}' (Total words: {total}) ---")
            
            # Print top prefixes
            pref_strs = []
            for fix, count in prefixes.most_common(top_k):
                pct = (count / total) * 100
                pref_strs.append(f"{fix} ({pct:.1f}%)")
            print(f"Top Prefixes: {', '.join(pref_strs)}")
            
            # Print top suffixes
            suff_strs = []
            for fix, count in suffixes.most_common(top_k):
                pct = (count / total) * 100
                suff_strs.append(f"{fix} ({pct:.1f}%)")
            print(f"Top Suffixes: {', '.join(suff_strs)}")

    # Run analysis for length 1 and 2
    for length in [1, 2]:
        print(f"\n\n\n{'#'*60}")
        print(f"### LENGTH {length} AFFIXES ###")
        print(f"{'#'*60}")
        analyze_group(by_language, "Language", n=length, top_k=5)
        analyze_group(by_scribe, "Scribe", n=length, top_k=5)
        analyze_group(by_category, "Category", n=length, top_k=5)

if __name__ == "__main__":
    with open(r'categorized_affix_analysis.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        main()
