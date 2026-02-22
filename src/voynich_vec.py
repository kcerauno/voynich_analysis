import logging
import sqlite3
import numpy as np
import matplotlib.pyplot as plt

from gensim.models import Word2Vec
from sklearn.manifold import TSNE


# ----------------------------
# 設定パラメータ
# ----------------------------

DB_PATH = r'data\voynich.db'

VECTOR_SIZE = 100
WINDOW_SIZE = 5
MIN_COUNT = 1
#SG = 1  # 1=skip-gram
SG = 0  # 0=CBOW
TSNE_PERPLEXITY = 20
TSNE_LR = 200
TSNE_ITER = 1000
RANDOM_STATE = 42


# ----------------------------
# ログ設定
# ----------------------------

logging.basicConfig(
    format='%(asctime)s : %(levelname)s : %(message)s',
    level=logging.INFO
)


# ----------------------------
# 1. SQLite からコーパス取得
# ----------------------------

def load_corpus_from_sqlite(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = """
        SELECT page, line_number, word_position, word||'_'||language as word
        FROM words_enriched
        ORDER BY page, line_number, word_position
    """

    cursor.execute(query)

    sentences = []
    current_key = None
    current_sentence = []

    for page, line_number, word_position, word in cursor.fetchall():
        key = (page, line_number)
        #key = page

        if key != current_key:
            if current_sentence:
                sentences.append(current_sentence)
            current_sentence = []
            current_key = key

        if word:
            current_sentence.append(word)

    if current_sentence:
        sentences.append(current_sentence)

    conn.close()

    print(f"Loaded {len(sentences)} sentences from SQLite.")
    return sentences


# ----------------------------
# 2. Word2Vec 学習
# ----------------------------

def train_word2vec(sentences):
    model = Word2Vec(
        sentences=sentences,
        vector_size=VECTOR_SIZE,
        window=WINDOW_SIZE,
        min_count=MIN_COUNT,
        sg=SG,
        workers=8,
        epochs=70
    )
    return model


# ----------------------------
# 3. t-SNE 可視化
# ----------------------------

def visualize_tsne(model, max_words=50000):
    words = list(model.wv.index_to_key)[:max_words]
    vectors = np.array([model.wv[w] for w in words])

    tsne = TSNE(
        n_components=2,
        perplexity=TSNE_PERPLEXITY,
        #learning_rate=TSNE_LR,
        learning_rate="auto",
        max_iter=TSNE_ITER,
        random_state=RANDOM_STATE
        #init="pca"
    )

    reduced = tsne.fit_transform(vectors)

    colors = []
    for word in words:
        if word.endswith("_A"):
            colors.append("red")
        elif word.endswith("_B"):
            colors.append("blue")
        else:
            colors.append("gray")

    plt.figure(figsize=(12, 10))
    #plt.scatter(reduced[:, 0], reduced[:, 1], s=10)
    plt.scatter(reduced[:, 0], reduced[:, 1], c=colors, s=10)

    plt.scatter([], [], c="red", label="A")
    plt.scatter([], [], c="blue", label="B")
    plt.scatter([], [], c="gray", label="Unknown")
    plt.legend()

    #for i, word in enumerate(words):
    #    plt.annotate(word, (reduced[i, 0], reduced[i, 1]), fontsize=8)

    plt.title("Voynich Word2Vec + t-SNE Visualization (SQLite)")
    #plt.show()
    plt.tight_layout()
    plt.savefig("voynich_tsne.png", dpi=300)
    print("Saved to voynich_tsne.png")

# ----------------------------
# メイン処理
# ----------------------------

def main():
    print("Loading corpus from SQLite...")
    sentences = load_corpus_from_sqlite(DB_PATH)

    print("Training Word2Vec...")
    model = train_word2vec(sentences)

    print("Visualizing with t-SNE...")
    visualize_tsne(model)


if __name__ == "__main__":
    main()