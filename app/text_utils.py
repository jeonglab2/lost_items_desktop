import unicodedata
import re
import mojimoji
import torch
from transformers import AutoTokenizer, AutoModel
import numpy as np

# 正規化関数
def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace('〜', '～')
    text = unicodedata.normalize('NFKC', text)
    text = mojimoji.zen_to_han(text, kana=False)
    text = text.lower()
    text = text.replace('ー', '')
    text = text.replace('ヴァ', 'バ').replace('ヴィ', 'ビ').replace('ヴェ', 'ベ').replace('ヴォ', 'ボ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# BERTベクトル化
MODEL_NAME = 'cl-tohoku/bert-base-japanese-whole-word-masking'
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME)
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

def get_bert_embedding(text: str) -> np.ndarray:
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=128)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
    cls_embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy()
    return cls_embedding.flatten()
