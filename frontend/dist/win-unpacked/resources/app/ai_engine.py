import json
import os
import numpy as np
from typing import Dict, List, Tuple, Optional
from PIL import Image
import torch
from transformers import pipeline
from sentence_transformers import SentenceTransformer
import easyocr
from ultralytics import YOLO
import cv2
from sklearn.metrics.pairwise import cosine_similarity
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIEngine:
    def __init__(self):
        """AIエンジンの初期化"""
        self.classification_data = self._load_classification_data()
        self.sentence_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        self.ocr_reader = easyocr.Reader(['ja', 'en'])
        
        # YOLOモデルの初期化（物体検出用）
        try:
            # backendディレクトリのyolov8n.ptを参照
            model_path = 'backend/yolov8n.pt'
            if os.path.exists(model_path):
                self.yolo_model = YOLO(model_path)
            else:
                logger.warning(f"YOLOモデルファイルが見つかりません: {model_path}")
                self.yolo_model = None
        except Exception as e:
            logger.warning(f"YOLOモデルの読み込みに失敗: {e}")
            self.yolo_model = None
        
        # 画像分類パイプライン
        try:
            self.image_classifier = pipeline(
                "image-classification",
                model="microsoft/resnet-50",
                device=0 if torch.cuda.is_available() else -1
            )
        except Exception as e:
            logger.warning(f"画像分類モデルの読み込みに失敗: {e}")
            self.image_classifier = None
    
    def _load_classification_data(self) -> Dict:
        """分類定義ファイルを読み込み"""
        try:
            # 本番環境ではresources配下のファイルを参照
            classification_file = 'docs/eac_05_item_classification.json'
            if os.path.exists(classification_file):
                with open(classification_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"分類定義ファイルが見つかりません: {classification_file}")
                return {"categories": []}
        except FileNotFoundError:
            logger.error("分類定義ファイルが見つかりません")
            return {"categories": []}
        except json.JSONDecodeError as e:
            logger.error(f"分類定義ファイルのJSON解析エラー: {e}")
            return {"categories": []}
    
    def recognize_item(self, image_path: str) -> Dict:
        """
        画像から拾得物を認識し、分類を提案
        
        Args:
            image_path: 画像ファイルのパス
            
        Returns:
            認識結果の辞書
        """
        try:
            # 画像の読み込み
            image = Image.open(image_path)
            
            # 1. 物体検出（YOLO）
            detected_objects = self._detect_objects(image)
            
            # 2. OCR（テキスト抽出）
            extracted_text = self._extract_text(image_path)
            
            # 3. 色分析
            dominant_colors = self._analyze_colors(image)
            
            # 4. 特徴抽出
            features = self._extract_features(image, detected_objects, extracted_text)
            
            # 5. 分類提案
            classification_result = self._classify_item(features)
            
            # 6. 信頼度計算
            confidence = self._calculate_confidence(classification_result, features)
            
            return {
                "category_large": classification_result.get("large_category", "その他"),
                "category_medium": classification_result.get("medium_category", "その他"),
                "name": classification_result.get("name", "不明"),
                "features": features,
                "color": dominant_colors[0] if dominant_colors else "不明",
                "confidence": confidence
            }
            
        except Exception as e:
            logger.error(f"画像認識エラー: {e}")
            return self._get_fallback_result()
    
    def _detect_objects(self, image: Image.Image) -> List[Dict]:
        """YOLOを使用した物体検出"""
        if not self.yolo_model:
            return []
        
        try:
            results = self.yolo_model(image)
            detected_objects = []
            
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        detected_objects.append({
                            "class": int(box.cls[0]),
                            "confidence": float(box.conf[0]),
                            "bbox": box.xyxy[0].tolist()
                        })
            
            return detected_objects
        except Exception as e:
            logger.warning(f"物体検出エラー: {e}")
            return []
    
    def _extract_text(self, image_path: str) -> str:
        """OCRを使用したテキスト抽出"""
        try:
            results = self.ocr_reader.readtext(image_path)
            extracted_text = " ".join([text[1] for text in results])
            return extracted_text
        except Exception as e:
            logger.warning(f"OCRエラー: {e}")
            return ""
    
    def _analyze_colors(self, image: Image.Image) -> List[str]:
        """画像の主要色を分析"""
        try:
            # 画像をリサイズして処理を高速化
            image_small = image.resize((100, 100))
            image_array = np.array(image_small)
            
            # 色の集計
            colors = image_array.reshape(-1, 3)
            
            # 主要色を抽出（簡易版）
            unique_colors, counts = np.unique(colors, axis=0, return_counts=True)
            dominant_indices = np.argsort(counts)[-5:]  # 上位5色
            
            color_names = []
            for idx in reversed(dominant_indices):
                r, g, b = unique_colors[idx]
                color_name = self._rgb_to_color_name(r, g, b)
                color_names.append(color_name)
            
            return color_names
        except Exception as e:
            logger.warning(f"色分析エラー: {e}")
            return ["不明"]
    
    def _rgb_to_color_name(self, r: int, g: int, b: int) -> str:
        """RGB値から色名を推定"""
        # 簡易的な色名マッピング
        color_map = {
            (255, 0, 0): "赤",
            (0, 255, 0): "緑", 
            (0, 0, 255): "青",
            (255, 255, 0): "黄",
            (255, 0, 255): "マゼンタ",
            (0, 255, 255): "シアン",
            (255, 255, 255): "白",
            (0, 0, 0): "黒",
            (128, 128, 128): "グレー",
            (255, 165, 0): "オレンジ",
            (128, 0, 128): "紫",
            (165, 42, 42): "茶",
        }
        
        # 最も近い色を探す
        min_distance = float('inf')
        closest_color = "不明"
        
        for (cr, cg, cb), color_name in color_map.items():
            distance = ((r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2) ** 0.5
            if distance < min_distance:
                min_distance = distance
                closest_color = color_name
        
        return closest_color
    
    def _extract_features(self, image: Image.Image, detected_objects: List[Dict], extracted_text: str) -> str:
        """画像から特徴を抽出"""
        features = []
        
        # 物体検出結果から特徴を抽出
        if detected_objects:
            object_classes = [obj["class"] for obj in detected_objects]
            features.append(f"検出物体: {len(detected_objects)}個")
        
        # OCR結果から特徴を抽出
        if extracted_text:
            features.append(f"テキスト: {extracted_text}")
        
        # 画像サイズ情報
        width, height = image.size
        features.append(f"サイズ: {width}x{height}")
        
        # 画像の形状特徴
        aspect_ratio = width / height
        if aspect_ratio > 1.5:
            features.append("横長")
        elif aspect_ratio < 0.7:
            features.append("縦長")
        else:
            features.append("正方形に近い")
        
        return ", ".join(features)
    
    def _classify_item(self, features: str) -> Dict:
        """特徴から分類を提案"""
        best_match = {
            "large_category": "その他",
            "medium_category": "その他",
            "name": "不明",
            "score": 0.0
        }
        
        # キーワードマッチング
        for category in self.classification_data.get("categories", []):
            large_category = category["large_category"]
            
            for medium_category_data in category["medium_categories"]:
                medium_category = medium_category_data["medium_category"]
                keywords = medium_category_data["keywords"]
                
                # キーワードマッチングスコアを計算
                score = self._calculate_keyword_score(features, keywords)
                
                if score > best_match["score"]:
                    best_match = {
                        "large_category": large_category,
                        "medium_category": medium_category,
                        "name": keywords[0] if keywords else "不明",
                        "score": score
                    }
        
        return best_match
    
    def _calculate_keyword_score(self, features: str, keywords: List[str]) -> float:
        """キーワードマッチングスコアを計算"""
        if not features or not keywords:
            return 0.0
        
        features_lower = features.lower()
        score = 0.0
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in features_lower:
                score += 1.0
            elif any(word in features_lower for word in keyword_lower.split()):
                score += 0.5
        
        return score / len(keywords) if keywords else 0.0
    
    def _calculate_confidence(self, classification_result: Dict, features: str) -> float:
        """分類結果の信頼度を計算"""
        base_confidence = classification_result.get("score", 0.0)
        
        # 特徴の豊富さによる補正
        feature_count = len(features.split(","))
        feature_bonus = min(feature_count * 0.1, 0.3)
        
        # 最終的な信頼度（0.0-1.0）
        confidence = min(base_confidence + feature_bonus, 1.0)
        
        return round(confidence, 2)
    
    def _get_fallback_result(self) -> Dict:
        """フォールバック結果を返す"""
        return {
            "category_large": "その他",
            "category_medium": "その他", 
            "name": "不明",
            "features": "認識できませんでした",
            "color": "不明",
            "confidence": 0.0
        }
    
    def generate_vector(self, text: str) -> List[float]:
        """
        テキストからベクトルを生成（セマンティック検索用）
        
        Args:
            text: ベクトル化するテキスト
            
        Returns:
            ベクトル（浮動小数点数のリスト）
        """
        try:
            if not text:
                return [0.0] * 384  # デフォルトベクトルサイズ
            
            # テキストをベクトル化
            vector = self.sentence_model.encode(text)
            return vector.tolist()
            
        except Exception as e:
            logger.error(f"ベクトル生成エラー: {e}")
            return [0.0] * 384
    
    def calculate_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        2つのベクトル間のコサイン類似度を計算
        
        Args:
            vec1: ベクトル1
            vec2: ベクトル2
            
        Returns:
            類似度スコア（0.0-1.0）
        """
        try:
            if not vec1 or not vec2 or len(vec1) != len(vec2):
                return 0.0
            
            # コサイン類似度を計算
            similarity = cosine_similarity([vec1], [vec2])[0][0]
            return float(similarity)
            
        except Exception as e:
            logger.error(f"類似度計算エラー: {e}")
            return 0.0
    
    def search_similar_items(self, query_text: str, item_vectors: List[Tuple[str, List[float]]]) -> List[Tuple[str, float]]:
        """
        セマンティック検索を実行
        
        Args:
            query_text: 検索クエリ
            item_vectors: (item_id, vector)のリスト
            
        Returns:
            (item_id, similarity_score)のリスト（類似度順）
        """
        try:
            # クエリをベクトル化
            query_vector = self.generate_vector(query_text)
            
            # 各アイテムとの類似度を計算
            similarities = []
            for item_id, item_vector in item_vectors:
                similarity = self.calculate_similarity(query_vector, item_vector)
                similarities.append((item_id, similarity))
            
            # 類似度で降順ソート
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            return similarities
            
        except Exception as e:
            logger.error(f"セマンティック検索エラー: {e}")
            return []

# グローバルAIエンジンインスタンス
ai_engine = AIEngine() 