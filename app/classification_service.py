import json
import os
import logging
from typing import Dict, List, Tuple, Optional
import mojimoji
import re

logger = logging.getLogger(__name__)

class ClassificationService:
    """
    決定論的かつ高性能な物品分類サービス
    eac_06_classification_system_design.md に基づいて実装
    - 正規化処理による表記ゆれの吸収
    - 正規表現による高速キーワードマッチング
    - 階層的優先度システム
    """
    def __init__(self):
        """サービスの初期化"""
        self.classification_data = self._load_classification_data()
        self.keyword_patterns, self.term_map = self._build_keyword_patterns()
        logger.info("分類サービスが初期化されました")

    def _load_classification_data(self) -> List[Dict]:
        """分類定義ファイルを読み込み"""
        classification_file = "frontend/public/item_classification.json"
        if os.path.exists(classification_file):
            with open(classification_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"分類定義ファイルを読み込みました: {classification_file}")
                return data
        logger.warning(f"分類定義ファイルが見つかりません: {classification_file}")
        return []

    def _build_keyword_patterns(self):
        """正規表現パターンを構築"""
        keyword_map = []  # (pattern, payload, medium_category_id, orig_term)
        term_map = {}
        for large_category in self.classification_data:
            large_category_id = large_category.get("large_category_id", "")
            large_category_name_ja = large_category.get("large_category_name_ja", "")
            for medium_category in large_category.get("medium_categories", []):
                medium_category_id = medium_category.get("medium_category_id", "")
                medium_category_name_ja = medium_category.get("medium_category_name_ja", "")
                priority = medium_category.get("priority", 0)
                for keyword_data in medium_category.get("keywords", []):
                    term = keyword_data.get("term", "")
                    weight = keyword_data.get("weight", 1.0)
                    if term:
                        payload = (
                            large_category_id,
                            large_category_name_ja,
                            medium_category_id,
                            medium_category_name_ja,
                            weight,
                            priority,
                            term
                        )
                        normalized_term = self._normalize_text(term)
                        # 正規表現パターンをエスケープして登録
                        pattern = re.escape(normalized_term)
                        keyword_map.append((pattern, payload, medium_category_id, term))
                        term_map[(normalized_term, medium_category_id)] = term
        # すべてのキーワードを|で連結したパターンを作成
        if keyword_map:
            or_pattern = "|".join([p[0] for p in keyword_map])
            compiled_pattern = re.compile(or_pattern)
        else:
            compiled_pattern = re.compile("")
        return (compiled_pattern, keyword_map), term_map

    def _normalize_text(self, text: str) -> str:
        """テキストを正規化する"""
        if not text:
            return ""
        # 1. 全角英数字記号を半角に
        text = mojimoji.zen_to_han(text, kana=False)
        # 2. 小文字に統一
        text = text.lower()
        # 3. カタカナの長音を削除
        text = text.replace('ー', '')
        # 4. ヴァ行の表記統一
        text = text.replace('ヴァ', 'バ').replace('ヴィ', 'ビ').replace('ヴェ', 'ベ').replace('ヴォ', 'ボ')
        # 5. 濁点・半濁点の正規化（簡易的）
        # ここでは省略（必要なら追加）
        # 6. 空白文字の正規化
        text = ''.join(text.split())
        return text

    def classify(self, text: str) -> Dict:
        """品名から分類を決定論的に推測"""
        if not text or not text.strip():
            return self._get_fallback_result()
        try:
            normalized_text = self._normalize_text(text)
            found_matches = []
            # 正規表現で全キーワードを一括検索
            for match in self.keyword_patterns[0].finditer(normalized_text):
                matched_str = match.group(0)
                # payloadを特定
                for pattern, payload, medium_category_id, orig_term in self.keyword_patterns[1]:
                    if matched_str == re.escape(self._normalize_text(orig_term)):
                        found_matches.append((match.end(), payload))
                        break
            if not found_matches:
                return self._get_fallback_result()
            best_match = self._select_best_match(found_matches, normalized_text)
            return best_match
        except Exception as e:
            logger.error(f"分類処理エラー: {e}")
            return self._get_fallback_result()

    def _select_best_match(self, matches: List[Tuple[int, tuple]], text: str) -> Dict:
        """マッチした結果から最適な分類を選択"""
        medium_category_scores = {}
        for end_index, (large_id, large_name, medium_id, medium_name, weight, priority, orig_term) in matches:
            keyword_length = len(orig_term)
            priority_factor = priority / 100.0 if priority > 0 else 0.01
            score = weight * keyword_length * priority_factor
            if medium_id not in medium_category_scores:
                medium_category_scores[medium_id] = {
                    "large_category_id": large_id,
                    "large_category_name_ja": large_name,
                    "medium_category_id": medium_id,
                    "medium_category_name_ja": medium_name,
                    "total_score": 0.0,
                    "priority": priority,
                    "matched_keywords": []
                }
            medium_category_scores[medium_id]["total_score"] += score
            medium_category_scores[medium_id]["matched_keywords"].append({
                "keyword": orig_term,
                "score": score
            })
        if not medium_category_scores:
            return self._get_fallback_result()
        best_medium_id = max(
            medium_category_scores.keys(),
            key=lambda x: (
                medium_category_scores[x]["total_score"],
                medium_category_scores[x]["priority"]
            )
        )
        best_match = medium_category_scores[best_medium_id]
        max_possible_score = 10  # 必要に応じて調整
        confidence = min(best_match["total_score"] / max_possible_score, 1.0)
        return {
            "large_category_id": best_match["large_category_id"],
            "large_category_name_ja": best_match["large_category_name_ja"],
            "medium_category_id": best_match["medium_category_id"],
            "medium_category_name_ja": best_match["medium_category_name_ja"],
            "confidence": round(confidence, 2),
            "matched_keywords": best_match["matched_keywords"]
        }

    def _get_fallback_result(self) -> Dict:
        """分類不能時のフォールバック結果を返す"""
        return {
            "large_category_id": "others",
            "large_category_name_ja": "その他",
            "medium_category_id": "items",
            "medium_category_name_ja": "その他",
            "confidence": 0,
            "matched_keywords": []
        }

    def get_all_categories(self) -> List[Dict]:
        """全分類情報を取得（フロントエンド用）"""
        return self.classification_data

# グローバル分類サービスインスタンス
classification_service = ClassificationService() 