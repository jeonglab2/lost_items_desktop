import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import numpy as np
from tqdm import tqdm
from text_utils import normalize_text, get_bert_embedding

def precompute_category_vectors(json_path: str, output_path: str):
    """item_classification.jsonからカテゴリベクトルを事前計算し保存する。"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # ネスト構造対応: 全キーワードを抽出
    categories = []
    for large in data:
        for medium in large.get("medium_categories", []):
            for keyword in medium.get("keywords", []):
                term = keyword.get("term")
                if term:
                    categories.append(term)

    category_vectors = []
    print(f"Pre-computing vectors for {len(categories)} categories...")
    for category in tqdm(categories):
        normalized_category = normalize_text(category)
        vector = get_bert_embedding(normalized_category)
        category_vectors.append(vector)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    np.savez(output_path, categories=np.array(categories), vectors=np.array(category_vectors))
    print(f"Saved pre-computed vectors to {output_path}")

if __name__ == "__main__":
    precompute_category_vectors(
        json_path="frontend/public/item_classification.json",
        output_path="data/category_vectors.npz"
    )
