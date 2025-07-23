# 高精度な拾得物分類推測を実現するための自然言語処理技術導入ガイド
## Executive Summary
`jeonglab2/lost_items_desktop`リポジトリにおける現在の拾得物分類機能は、ユーザーの入力文字列と`item_classification.json`内の`term`との完全一致、または部分一致に依存する単純な字句マッチングに基づいています。
このアプローチは、「めがねケース」と「眼鏡ケース」のように、同じ対象物を指すにもかかわらず漢字、平仮名、片仮名といった表記の違いを吸収できず、結果として分類精度が著しく低いという問題を抱えています。

本ドキュメントでは、この課題を解決し、高精度な分類推測機能を実現するため、従来の字句マッチングから意味的類似度に基づくシステムへの移行を提案します。
この移行は、以下の4段階からなる自然言語処理（NLP）パイプラインの導入によって達成されます。

1. テキスト正規化（ **Text Normalization** ）: ユーザー入力と分類カテゴリの両方を、表記の揺れ（例：全角・半角、大文字・小文字）を排除した統一的な「正準形式」に変換します。
2. 形態素解析（ **Morphological Analysis** ）: 正規化されたテキストを言語的な最小単位である形態素に分解し、各単語の品詞や基本形（原形）を抽出します。これにより、「失くした財布」という入力から核心的な名詞「財布」を特定できます。
3. 意味のベクトル化（ **Semantic Vectorization** ）: 形態素解析によって得られた単語や文を、BERTのような最新の言語モデルを用いて数値ベクトル（埋め込み表現）に変換します。このベクトルは単語や文の「意味」を多次元空間上の座標として表現します。
4. 類似度計算（ **Similarity Calculation** ）: ユーザー入力のベクトルと、事前に計算しておいた全分類カテゴリのベクトルとを、コサイン類似度を用いて比較します。これにより、意味的に最も近いカテゴリをスコア順にランキングし、ユーザーに提示することが可能になります。

このセマンティック（意味論的）アプローチを導入することで、システムは単語の表面的な文字列ではなく、その背後にある意味を理解できるようになります。
結果として、表記の揺れに頑健で、より直感的かつ効果的な分類推測が可能となり、アプリケーションのユーザーエクスペリエンスが大幅に向上することが期待されます。

## 第1章: 堅牢な入力処理のためのテキスト正規化パイプラインの構築
高精度な自然言語処理システムの構築は、入力されるテキストをいかに一貫性のある形式に整えるかにかかっています。
この最初のステップである「テキスト正規化」は、後続の形態素解析や意味解析の精度を直接左右する極めて重要な工程です。

### 1.1 正規化の核心的要素
- Unicode正規化: `unicodedata.normalize('NFKC', text)` を使用し、全角・半角の英数字や互換文字を統一的な形式に変換します。
- 文字種の変換: `mojimoji`ライブラリなどを用いて、全角・半角カタカナなどを要件に応じて制御します。
- 大文字・小文字の統一: `text.lower()` を用いてアルファベットを小文字に統一し、大文字・小文字の違いによる検索漏れを防ぎます。

### 1.2 実装戦略とコード例

```python
import unicodedata
import re

def normalize_text(text: str) -> str:
    """
    日本語テキストを正規化する総合的な関数。
    1. 波ダッシュなどの特定の記号を統一
    2. NFKC形式でUnicode正規化
    3. アルファベットを小文字に統一
    4. 連続する空白を1つにまとめる
    """
    if not isinstance(text, str):
        return ""
        
    # 1. 特定の記号の統一
    text = text.replace('〜', '～')

    # 2. NFKC形式でUnicode正規化
    text = unicodedata.normalize('NFKC', text)
    
    # 3. アルファベットを小文字に統一
    text = text.lower()
    
    # 4. 連続する空白を1つにまとめる
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text
```

## 第2章: 形態素解析による核心的特徴抽出
テキスト正規化の後、文を言語的な最小単位である「形態素」に分割し、品詞や基本形（原形）を抽出します。
これにより、「青い傘を失くした」という入力から核心的な名詞「傘」を特定できます。

### 2.1 日本語形態素解析ツールの比較

| 特徴 | **MeCab (+neologd)** | **Juman++** | **SudachiPy** | **Janome** |
| コアエンジン | C++ | C++ | Rust (Pythonバインディング) | Pure Python | 
| 主な強み | 処理速度、豊富な辞書エコシステム | 高い解析精度 | バランス、モダンな機能、導入容易性 | 導入の容易さ | 
| 本プロジェクトへの推奨度 | 可 | 可 | 優 | - |

結論: 高精度、導入容易性、豊富な機能のバランスに優れる **SudachiPy** の採用を強く推奨します。

### 2.2 実装と推奨ツール

```
# pip install sudachipy sudachidict_core
```

```python
from sudachipy import Dictionary, SplitMode

# 辞書オブジェクトの作成（core辞書を使用）
tokenizer_obj = Dictionary(dict="core").create()

def extract_nouns(text: str) -> list[str]:
    """
    SudachiPyを使用してテキストから名詞の原形を抽出する。
    """
    morphemes = tokenizer_obj.tokenize(text, SplitMode.C)
    nouns = [m.dictionary_form() for m in morphemes if m.part_of_speech()[0] == '名詞']
    return nouns
```

注意点: 使用する形態素解析器は、次章で選択する単語埋め込みモデルが学習時に使用したものと整合性を取る必要があります。

## 第3章: 単語埋め込みモデルによる意味的類似度検索の実装
単語をその「意味」を表す数値ベクトル（単語埋め込み）に変換し、ベクトル空間での近さ（コサイン類似度）を計算することで、「めがねケース」と「眼鏡ケース」のような同義語を同一視します。

### 3.1 単語埋め込みモデルの比較

| 特徴 |**Word2Vec / fastText** | **BERT** | 
| 埋め込みタイプ | 静的 | 文脈依存 | 
| 多義性対応 | 不可 | 可能 | 
| 高精度タスクへの推奨度| 良 | 最良 | 

結論: 文脈を理解し多義性を解決できる **BERT** の採用が最も合理的です。Hugging Faceの`transformers`ライブラリと、東北大学などが公開する日本語事前学習済みモデルを利用します。

### 3.2 実装：BERTによるベクトル化と類似度計算

#### ステップ1: 環境構築とモデルのロード

```
pip install torch transformers[ja] scipy scikit-learn
```

```python
import torch
from transformers import AutoTokenizer, AutoModel

MODEL_NAME = 'cl-tohoku/bert-base-japanese-whole-word-masking'
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME)
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)
```

#### ステップ2: テキストのベクトル化

```python
import numpy as np

def get_bert_embedding(text: str) -> np.ndarray:
    """BERTを用いてテキストの[CLS]トークンの埋め込みベクトルを取得する。"""
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=128)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
    cls_embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy()
    return cls_embedding.flatten()
```

#### ステップ3: コサイン類似度の計算と候補のランキング

```python
from sklearn.metrics.pairwise import cosine_similarity

def suggest_categories_by_similarity(user_input: str, category_vectors: dict, top_n: int = 3):
    input_vector = get_bert_embedding(user_input)
    similarities = {}
    for category, cat_vector in category_vectors.items():
        sim = cosine_similarity([input_vector], [cat_vector])[0][0]
        similarities[category] = sim
    sorted_suggestions = sorted(similarities.items(), key=lambda item: item[1], reverse=True)
    return sorted_suggestions[:top_n]
```

## 第4章: システム統合とパフォーマンス最適化
BERTによるベクトル化は計算コストが高いため、応答性を確保するための最適化が不可欠です。

### 4.1 パフォーマンスのボトルネックと解決策：事前計算とキャッシング
戦略: アプリケーションのビルド時または初回起動時に、静的なデータである`item_classification.json`の全カテゴリのベクトルを一度だけ計算し、その結果をファイル（例: `category_vectors.npz`）に保存します。
実行時にはこの事前計算済みファイルを読み込むことで、リアルタイム処理をユーザー入力のベクトル化のみに限定します。

事前計算スクリプト

```python
import json
import numpy as np
from tqdm import tqdm

def precompute_category_vectors(json_path: str, output_path: str):
    """item_classification.jsonからカテゴリベクトルを事前計算し保存する。"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    categories = [item['term'] for item in data]
    category_vectors = []
    
    print(f"Pre-computing vectors for {len(categories)} categories...")
    for category in tqdm(categories):
        normalized_category = normalize_text(category)
        vector = get_bert_embedding(normalized_category)
        category_vectors.append(vector)
        
    np.savez(output_path, categories=np.array(categories), vectors=np.array(category_vectors))
    print(f"Saved pre-computed vectors to {output_path}")

# 実行
# precompute_category_vectors('frontend/public/item_classification.json', 'data/category_vectors.npz')
```

### 4.2 最終的な実装アーキテクチャ
関連処理を一つのクラスにカプセル化し、見通しとメンテナンス性を向上させます。

```python
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class SemanticClassifier:
    def __init__(self, precomputed_vectors_path: str):
        """分類器を初期化し、事前計算済みベクトルをロードする。"""
        try:
            data = np.load(precomputed_vectors_path)
            self.categories = data['categories']
            self.category_vectors = data['vectors']
        except FileNotFoundError:
            print(f"Error: Pre-computed vectors file not found at {precomputed_vectors_path}")
            self.categories = np.array([])
            self.category_vectors = np.array([])
    
    def suggest_categories(self, user_input: str, top_n: int = 5) -> list[tuple[str, float]]:
        """ユーザー入力に基づいて、意味的に類似したカテゴリを提案する。"""
        if self.category_vectors.size == 0:
            return []
            
        normalized_input = normalize_text(user_input)
        input_vector = get_bert_embedding(normalized_input)
        
        similarities = cosine_similarity(input_vector.reshape(1, -1), self.category_vectors).flatten()
        
        top_n_indices = np.argsort(similarities)[-top_n:][::-1]
        
        suggestions = [(self.categories[i], float(similarities[i])) for i in top_n_indices]
        return suggestions

# アプリケーションでの使用例
# classifier = SemanticClassifier('data/category_vectors.npz')
# top_suggestions = classifier.suggest_categories("スマホを落とした")
# print(top_suggestions)
```

## 結論と今後の展望
### 結論
提案したNLPパイプライン（正規化 → 形態素解析 → BERTによるベクトル化 → 類似度計算）と事前計算アーキテクチャは、現在の字句マッチングが抱える問題を根本的に解決し、高精度で応答性の高い分類推測機能を実現します。

### 今後の展望
- ユーザーフィードバックによる継続的なモデル改善: ユーザーの選択データを収集し、BERTモデルをファインチューニングすることで、ドメイン特化の精度向上を目指します。
- より複雑な問い合わせへの対応: 質問応答（QA）モデルを活用し、詳細な文章入力から直接アイテム名を抽出します。分類カテゴリの拡張と管理: カテゴリ追加時に事前計算スクリプトを再実行するプロセスを整備・自動化します。