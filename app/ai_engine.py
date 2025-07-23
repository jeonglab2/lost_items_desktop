import os
import sys

# vendorディレクトリをimportパスに追加
vendor_path = os.path.join(os.path.dirname(__file__), 'vendor')
if vendor_path not in sys.path:
    sys.path.insert(0, vendor_path)

import json
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
import mojimoji
import re
from app.classification_service import SemanticClassifier

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIEngine:
    def __init__(self):
        """AIエンジンの初期化"""
        self.classification_data = self._load_classification_data()
        self.sentence_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        self.semantic_classifier = SemanticClassifier('data/category_vectors.npz')
        
        # EasyOCRの初期化（PIL.Image.ANTIALIASエラー回避）
        try:
            # Pillowの新しいバージョンでANTIALIASが削除されたため、代替設定を使用
            import PIL.Image
            if not hasattr(PIL.Image, 'ANTIALIAS'):
                # ANTIALIASが存在しない場合、LANCZOSを使用
                PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
            
            self.ocr_reader = easyocr.Reader(['ja', 'en'])
        except Exception as e:
            logger.warning(f"EasyOCRの初期化に失敗: {e}")
            self.ocr_reader = None
        
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
        
        # 分類オートマトンの構築（エラーハンドリング付き）
        try:
            self.classification_automaton = self._build_classification_automaton()
            logger.info(f"分類オートマトン構築完了: {len(self.classification_automaton[1])}個のキーワード")
        except Exception as e:
            logger.error(f"分類オートマトン初期化エラー: {e}")
            # エラーが発生した場合は空のオートマトンを設定
            self.classification_automaton = (re.compile(""), [])
    
    def _load_classification_data(self) -> Dict:
        """分類定義ファイルを読み込み"""
        try:
            # 1. 開発用パス
            dev_path = os.path.join(os.path.dirname(__file__), '../frontend/public/item_classification.json')
            # 2. 配布用パス（resources/app/ など）
            packaged_path = os.path.join(os.path.dirname(__file__), 'item_classification.json')
            # 3. カレントディレクトリ直下
            cwd_path = os.path.join(os.getcwd(), 'item_classification.json')

            for path in [dev_path, packaged_path, cwd_path]:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        logger.info(f"分類定義ファイルを読み込みました: {path}")
                        return data

            logger.warning("分類定義ファイルが見つかりません: " +
                           f"{dev_path}, {packaged_path}, {cwd_path}")
            return []
        except Exception as e:
            logger.error(f"分類データ読み込みエラー: {e}")
            return []
    
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
            
            # 3. 色分析（物体領域に限定）
            dominant_colors = self._analyze_colors(image, detected_objects)
            
            # 4. 特徴抽出
            features = self._extract_features(image, detected_objects, extracted_text)
            
            # 5. 分類提案
            classification_result = self._classify_item(features, detected_objects)
            
            # 6. 信頼度計算
            confidence = self._calculate_confidence(classification_result, features, detected_objects)
            
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
            
            # 拾得物として適切な物品のクラスID
            relevant_class_ids = {
                67,  # cell phone
                63,  # laptop
                64,  # mouse
                66,  # keyboard
                65,  # remote
                62,  # tv
                26,  # handbag
                24,  # backpack
                28,  # suitcase
                25,  # umbrella
                73,  # book
                74,  # clock
                39,  # bottle
                41,  # cup
                40,  # wine glass
                45,  # bowl
                27,  # tie
                32,  # sports ball
                29,  # frisbee
                30,  # skis
                31,  # snowboard
                36,  # skateboard
                37,  # surfboard
                38,  # tennis racket
                34,  # baseball bat
                35,  # baseball glove
                46,  # banana
                47,  # apple
                48,  # sandwich
                49,  # orange
                50,  # broccoli
                51,  # carrot
                52,  # hot dog
                53,  # pizza
                54,  # donut
                55,  # cake
                76,  # scissors
                77,  # teddy bear
                78,  # hair drier
                79,  # toothbrush
                75,  # vase
                1,   # bicycle
            }
            
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        class_id = int(box.cls[0])
                        confidence = float(box.conf[0])
                        bbox = box.xyxy[0].tolist()
                        
                        # 信頼度が0.3以上で、拾得物として適切な物品のみを検出
                        if confidence >= 0.3 and class_id in relevant_class_ids:
                            # YOLOのクラス名を取得
                            class_name = self._get_yolo_class_name(class_id)
                            
                            detected_objects.append({
                                "class_id": class_id,
                                "class_name": class_name,
                                "confidence": confidence,
                                "bbox": bbox
                            })
            
            return detected_objects
        except Exception as e:
            logger.warning(f"物体検出エラー: {e}")
            return []
    
    def _get_yolo_class_name(self, class_id: int) -> str:
        """YOLOのクラスIDからクラス名を取得"""
        # YOLO COCOデータセットのクラス名（拾得物として適切な物品を優先）
        coco_classes = {
            # 携帯電話・電子機器類（優先度高）
            67: "cell phone",  # 携帯電話
            63: "laptop",      # ノートパソコン
            64: "mouse",       # マウス
            66: "keyboard",    # キーボード
            65: "remote",      # リモコン
            62: "tv",          # テレビ
            
            # かばん・バッグ類（優先度高）
            26: "handbag",     # ハンドバッグ
            24: "backpack",    # リュックサック
            28: "suitcase",    # スーツケース
            
            # 傘類（優先度高）
            25: "umbrella",    # 傘
            
            # 本・書類類（優先度中）
            73: "book",        # 本
            
            # 時計類（優先度中）
            74: "clock",       # 時計
            
            # 食器・容器類（優先度中）
            39: "bottle",      # ボトル
            41: "cup",         # カップ
            40: "wine glass",  # ワイングラス
            45: "bowl",        # ボウル
            
            # 衣類・アクセサリー類（優先度中）
            27: "tie",         # ネクタイ
            
            # スポーツ用品類（優先度低）
            32: "sports ball", # スポーツボール
            29: "frisbee",     # フリスビー
            30: "skis",        # スキー
            31: "snowboard",   # スノーボード
            36: "skateboard",  # スケートボード
            37: "surfboard",   # サーフボード
            38: "tennis racket", # テニスラケット
            34: "baseball bat", # 野球バット
            35: "baseball glove", # 野球グローブ
            
            # 楽器類（優先度低）
            # 楽器はCOCOデータセットに含まれていないため、別途対応が必要
            
            # 食品類（優先度低）
            46: "banana",      # バナナ
            47: "apple",       # りんご
            48: "sandwich",    # サンドイッチ
            49: "orange",      # オレンジ
            50: "broccoli",    # ブロッコリー
            51: "carrot",      # にんじん
            52: "hot dog",     # ホットドッグ
            53: "pizza",       # ピザ
            54: "donut",       # ドーナツ
            55: "cake",        # ケーキ
            
            # 家具類（優先度低）
            56: "chair",       # 椅子
            57: "couch",       # ソファ
            58: "potted plant", # 鉢植え
            59: "bed",         # ベッド
            60: "dining table", # テーブル
            75: "vase",        # 花瓶
            
            # 家電・設備類（優先度低）
            68: "microwave",   # 電子レンジ
            69: "oven",        # オーブン
            70: "toaster",     # トースター
            71: "sink",        # シンク
            72: "refrigerator", # 冷蔵庫
            78: "hair drier",  # ヘアドライヤー
            79: "toothbrush",  # 歯ブラシ
            
            # 工具・文具類（優先度低）
            76: "scissors",    # ハサミ
            
            # 生物・人物類（優先度最低）
            0: "person",       # 人物
            14: "bird",        # 鳥
            15: "cat",         # 猫
            16: "dog",         # 犬
            17: "horse",       # 馬
            18: "sheep",       # 羊
            19: "cow",         # 牛
            20: "elephant",    # 象
            21: "bear",        # 熊
            22: "zebra",       # シマウマ
            23: "giraffe",     # キリン
            77: "teddy bear",  # テディベア
            
            # 乗り物類（優先度最低）
            1: "bicycle",      # 自転車
            2: "car",          # 車
            3: "motorcycle",   # バイク
            4: "airplane",     # 飛行機
            5: "bus",          # バス
            6: "train",        # 電車
            7: "truck",        # トラック
            8: "boat",         # ボート
            
            # 道路・交通関連（優先度最低）
            9: "traffic light", # 信号機
            10: "fire hydrant", # 消火栓
            11: "stop sign",   # 停止標識
            12: "parking meter", # パーキングメーター
            13: "bench",       # ベンチ
            61: "toilet",      # トイレ
        }
        return coco_classes.get(class_id, f"class_{class_id}")
    
    def _extract_text(self, image_path: str) -> str:
        """OCRを使用したテキスト抽出"""
        if not self.ocr_reader:
            return ""
            
        try:
            results = self.ocr_reader.readtext(image_path)
            extracted_text = " ".join([text[1] for text in results])
            return extracted_text
        except Exception as e:
            logger.warning(f"OCRエラー: {e}")
            return ""
    
    def _analyze_colors(self, image: Image.Image, detected_objects: List[Dict]) -> List[str]:
        """画像の主要色を分析（物体領域に限定）"""
        try:
            # 物体が検出された場合、物体領域の色を分析
            if detected_objects:
                # 最も信頼度の高い物体の領域を使用
                best_object = max(detected_objects, key=lambda x: x["confidence"])
                bbox = best_object["bbox"]
                
                # バウンディングボックスで画像をクロップ
                x1, y1, x2, y2 = map(int, bbox)
                cropped_image = image.crop((x1, y1, x2, y2))
                
                # クロップした画像の色を分析
                return self._analyze_image_colors(cropped_image)
            else:
                # 物体が検出されない場合、全体の色を分析
                return self._analyze_image_colors(image)
                
        except Exception as e:
            logger.warning(f"色分析エラー: {e}")
            return ["不明"]
    
    def _analyze_image_colors(self, image: Image.Image) -> List[str]:
        """画像の色を分析"""
        try:
            # 画像をリサイズして処理を高速化
            image_small = image.resize((100, 100))
            image_array = np.array(image_small)
            
            # RGB形式に変換
            if len(image_array.shape) == 3 and image_array.shape[2] == 3:
                colors = image_array.reshape(-1, 3)
            else:
                # グレースケールの場合
                colors = np.stack([image_array.flatten()] * 3, axis=1)
            
            # 主要色を抽出（簡易版）
            unique_colors, counts = np.unique(colors, axis=0, return_counts=True)
            dominant_indices = np.argsort(counts)[-5:]  # 上位5色
            
            color_names = []
            for idx in reversed(dominant_indices):
                r, g, b = unique_colors[idx]
                color_name = self._rgb_to_color_name(r, g, b)
                if color_name not in color_names:  # 重複を避ける
                    color_names.append(color_name)
            
            return color_names[:3]  # 上位3色のみ返す
        except Exception as e:
            logger.warning(f"画像色分析エラー: {e}")
            return ["不明"]
    
    def _rgb_to_color_name(self, r: int, g: int, b: int) -> str:
        """RGB値から色名を推定"""
        # より詳細な色名マッピング
        color_map = {
            (255, 0, 0): "赤", (200, 0, 0): "赤", (150, 0, 0): "赤",
            (0, 255, 0): "緑", (0, 200, 0): "緑", (0, 150, 0): "緑",
            (0, 0, 255): "青", (0, 0, 200): "青", (0, 0, 150): "青",
            (255, 255, 0): "黄", (200, 200, 0): "黄", (150, 150, 0): "黄",
            (255, 0, 255): "マゼンタ", (200, 0, 200): "マゼンタ", (150, 0, 150): "マゼンタ",
            (0, 255, 255): "シアン", (0, 200, 200): "シアン", (0, 150, 150): "シアン",
            (255, 255, 255): "白", (240, 240, 240): "白", (220, 220, 220): "白",
            (0, 0, 0): "黒", (20, 20, 20): "黒", (40, 40, 40): "黒",
            (128, 128, 128): "グレー", (100, 100, 100): "グレー", (150, 150, 150): "グレー",
            (255, 165, 0): "オレンジ", (255, 140, 0): "オレンジ", (255, 120, 0): "オレンジ",
            (128, 0, 128): "紫", (100, 0, 100): "紫", (150, 0, 150): "紫",
            (165, 42, 42): "茶", (139, 69, 19): "茶", (160, 82, 45): "茶",
            (255, 192, 203): "ピンク", (255, 182, 193): "ピンク", (255, 172, 183): "ピンク",
            (255, 215, 0): "金", (255, 223, 0): "金", (255, 235, 0): "金",
            (192, 192, 192): "銀", (169, 169, 169): "銀", (211, 211, 211): "銀",
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
            object_names = [obj["class_name"] for obj in detected_objects]
            features.extend(object_names)
            features.append(f"検出物体数: {len(detected_objects)}個")
            
            # 検出された物体のサイズ情報を追加
            for i, obj in enumerate(detected_objects):
                bbox = obj["bbox"]
                x1, y1, x2, y2 = bbox
                width = x2 - x1
                height = y2 - y1
                object_name = obj["class_name"]
                features.append(f"{object_name}サイズ: {int(width)}x{int(height)}px")
        
        # OCR結果から特徴を抽出
        if extracted_text:
            features.append(f"テキスト: {extracted_text}")
        
        # 画像の形状特徴
        width, height = image.size
        aspect_ratio = width / height
        if aspect_ratio > 1.5:
            features.append("横長")
        elif aspect_ratio < 0.7:
            features.append("縦長")
        else:
            features.append("正方形に近い")
        
        return ", ".join(features)
    
    def _classify_item(self, features: str, detected_objects: List[Dict]) -> Dict:
        """特徴から分類を提案"""
        best_match = {
            "large_category": "その他",
            "medium_category": "その他",
            "name": "不明",
            "score": 0.0
        }
        
        # 物体検出結果を優先的に使用
        if detected_objects:
            object_classification = self._classify_by_objects(detected_objects)
            if object_classification["score"] > 0.0:
                return object_classification
        
        # キーワードマッチング（新しい分類データ構造に対応）
        for category in self.classification_data:
            large_category = category["large_category_name_ja"]
            
            for medium_category_data in category["medium_categories"]:
                medium_category = medium_category_data["medium_category_name_ja"]
                keywords = [kw["term"] for kw in medium_category_data["keywords"]]
                
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
    
    def _classify_by_objects(self, detected_objects: List[Dict]) -> Dict:
        """物体検出結果から分類を提案"""
        # YOLOクラス名と分類のマッピング（item_classification.jsonに基づく）
        object_to_category = {
            # 携帯電話類（優先度最高）
            "cell phone": {"large": "携帯電話類", "medium": "携帯電話機", "name": "スマートフォン"},
            
            # 電気製品類
            "laptop": {"large": "電気製品類", "medium": "電子機器", "name": "ノートパソコン"},
            "keyboard": {"large": "電気製品類", "medium": "電子機器", "name": "キーボード"},
            "mouse": {"large": "電気製品類", "medium": "電子機器", "name": "マウス"},
            "remote": {"large": "電気製品類", "medium": "その他電気製品", "name": "リモコン"},
            "tv": {"large": "電気製品類", "medium": "その他電気製品", "name": "テレビ"},
            "hair drier": {"large": "電気製品類", "medium": "その他電気製品", "name": "ヘアドライヤー"},
            "toothbrush": {"large": "生活用品類", "medium": "生活用品", "name": "歯ブラシ"},
            
            # かばん類
            "handbag": {"large": "かばん類", "medium": "手提げかばん", "name": "ハンドバッグ"},
            "backpack": {"large": "かばん類", "medium": "肩掛けかばん", "name": "リュックサック"},
            "suitcase": {"large": "かばん類", "medium": "その他かばん類", "name": "スーツケース"},
            
            # 傘類
            "umbrella": {"large": "かさ類", "medium": "かさ", "name": "傘"},
            
            # 時計類
            "clock": {"large": "時計類", "medium": "その他時計類", "name": "時計"},
            
            # 著作品類
            "book": {"large": "著作品類", "medium": "書籍類", "name": "本"},
            
            # 食器・容器類
            "bottle": {"large": "生活用品類", "medium": "食器類", "name": "ボトル"},
            "cup": {"large": "生活用品類", "medium": "食器類", "name": "カップ"},
            "wine glass": {"large": "生活用品類", "medium": "食器類", "name": "ワイングラス"},
            "bowl": {"large": "生活用品類", "medium": "食器類", "name": "ボウル"},
            
            # 衣類・アクセサリー類
            "tie": {"large": "衣類・履物類", "medium": "その他衣類", "name": "ネクタイ"},
            
            # スポーツ用品類
            "sports ball": {"large": "趣味・娯楽用品類", "medium": "レジャー・スポーツ用品", "name": "スポーツボール"},
            "frisbee": {"large": "趣味・娯楽用品類", "medium": "レジャー・スポーツ用品", "name": "フリスビー"},
            "skis": {"large": "趣味・娯楽用品類", "medium": "レジャー・スポーツ用品", "name": "スキー"},
            "snowboard": {"large": "趣味・娯楽用品類", "medium": "レジャー・スポーツ用品", "name": "スノーボード"},
            "skateboard": {"large": "趣味・娯楽用品類", "medium": "レジャー・スポーツ用品", "name": "スケートボード"},
            "surfboard": {"large": "趣味・娯楽用品類", "medium": "レジャー・スポーツ用品", "name": "サーフボード"},
            "tennis racket": {"large": "趣味・娯楽用品類", "medium": "レジャー・スポーツ用品", "name": "テニスラケット"},
            "baseball bat": {"large": "趣味・娯楽用品類", "medium": "レジャー・スポーツ用品", "name": "野球バット"},
            "baseball glove": {"large": "趣味・娯楽用品類", "medium": "レジャー・スポーツ用品", "name": "野球グローブ"},
            
            # 食品類
            "banana": {"large": "食料品類", "medium": "食料品類", "name": "バナナ"},
            "apple": {"large": "食料品類", "medium": "食料品類", "name": "りんご"},
            "sandwich": {"large": "食料品類", "medium": "食料品類", "name": "サンドイッチ"},
            "orange": {"large": "食料品類", "medium": "食料品類", "name": "オレンジ"},
            "broccoli": {"large": "食料品類", "medium": "食料品類", "name": "ブロッコリー"},
            "carrot": {"large": "食料品類", "medium": "食料品類", "name": "にんじん"},
            "hot dog": {"large": "食料品類", "medium": "食料品類", "name": "ホットドッグ"},
            "pizza": {"large": "食料品類", "medium": "食料品類", "name": "ピザ"},
            "donut": {"large": "食料品類", "medium": "食料品類", "name": "ドーナツ"},
            "cake": {"large": "食料品類", "medium": "食料品類", "name": "ケーキ"},
            
            # 生活用品類
            "scissors": {"large": "生活用品類", "medium": "工具類", "name": "ハサミ"},
            "vase": {"large": "生活用品類", "medium": "生活用品", "name": "花瓶"},
            
            # 趣味・娯楽用品類
            "teddy bear": {"large": "趣味・娯楽用品類", "medium": "その他趣味・娯楽用品類", "name": "ぬいぐるみ"},
            
            # 動植物類（優先度低）
            "person": {"large": "その他", "medium": "その他", "name": "人物"},
            "bird": {"large": "動植物類", "medium": "動物", "name": "鳥"},
            "cat": {"large": "動植物類", "medium": "動物", "name": "猫"},
            "dog": {"large": "動植物類", "medium": "動物", "name": "犬"},
            "horse": {"large": "動植物類", "medium": "動物", "name": "馬"},
            "sheep": {"large": "動植物類", "medium": "動物", "name": "羊"},
            "cow": {"large": "動植物類", "medium": "動物", "name": "牛"},
            "elephant": {"large": "動植物類", "medium": "動物", "name": "象"},
            "bear": {"large": "動植物類", "medium": "動物", "name": "熊"},
            "zebra": {"large": "動植物類", "medium": "動物", "name": "シマウマ"},
            "giraffe": {"large": "動植物類", "medium": "動物", "name": "キリン"},
            "potted plant": {"large": "動植物類", "medium": "植物", "name": "鉢植え"},
            
            # 乗り物類（優先度最低）
            "bicycle": {"large": "生活用品類", "medium": "自転車類", "name": "自転車"},
            "car": {"large": "その他", "medium": "その他", "name": "車"},
            "motorcycle": {"large": "その他", "medium": "その他", "name": "バイク"},
            "airplane": {"large": "その他", "medium": "その他", "name": "飛行機"},
            "bus": {"large": "その他", "medium": "その他", "name": "バス"},
            "train": {"large": "その他", "medium": "その他", "name": "電車"},
            "truck": {"large": "その他", "medium": "その他", "name": "トラック"},
            "boat": {"large": "その他", "medium": "その他", "name": "ボート"},
            
            # 家具・設備類（優先度最低）
            "chair": {"large": "その他", "medium": "その他", "name": "椅子"},
            "couch": {"large": "その他", "medium": "その他", "name": "ソファ"},
            "bed": {"large": "その他", "medium": "その他", "name": "ベッド"},
            "dining table": {"large": "その他", "medium": "その他", "name": "テーブル"},
            "microwave": {"large": "その他", "medium": "その他", "name": "電子レンジ"},
            "oven": {"large": "その他", "medium": "その他", "name": "オーブン"},
            "toaster": {"large": "その他", "medium": "その他", "name": "トースター"},
            "sink": {"large": "その他", "medium": "その他", "name": "シンク"},
            "refrigerator": {"large": "その他", "medium": "その他", "name": "冷蔵庫"},
            "toilet": {"large": "その他", "medium": "その他", "name": "トイレ"},
            
            # 道路・交通関連（優先度最低）
            "traffic light": {"large": "その他", "medium": "その他", "name": "信号機"},
            "fire hydrant": {"large": "その他", "medium": "その他", "name": "消火栓"},
            "stop sign": {"large": "その他", "medium": "その他", "name": "停止標識"},
            "parking meter": {"large": "その他", "medium": "その他", "name": "パーキングメーター"},
            "bench": {"large": "その他", "medium": "その他", "name": "ベンチ"},
        }
        
        best_score = 0.0
        best_category = {
            "large_category": "その他",
            "medium_category": "その他",
            "name": "不明",
            "score": 0.0
        }
        
        # 拾得物として適切な物品の優先度を設定
        priority_items = {
            "cell phone", "laptop", "handbag", "backpack", "suitcase", "umbrella",
            "book", "clock", "bottle", "cup", "tie", "scissors", "teddy bear"
        }
        
        for obj in detected_objects:
            class_name = obj["class_name"]
            confidence = obj["confidence"]
            
            if class_name in object_to_category:
                category_info = object_to_category[class_name]
                
                # 優先度に基づいてスコアを調整
                base_score = confidence
                if class_name in priority_items:
                    # 優先物品はスコアを1.2倍に
                    score = base_score * 1.2
                else:
                    # その他の物品はスコアを0.8倍に
                    score = base_score * 0.8
                
                if score > best_score:
                    best_score = score
                    best_category = {
                        "large_category": category_info["large"],
                        "medium_category": category_info["medium"],
                        "name": category_info["name"],
                        "score": score
                    }
        
        return best_category
    
    def _calculate_keyword_score(self, features: str, keywords: List[str]) -> float:
        """キーワードマッチングスコアを計算"""
        if not features or not keywords:
            return 0.0
        
        features_lower = features.lower()
        score = 0.0
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            # 完全一致（最高スコア）
            if keyword_lower == features_lower:
                score += 2.0
            # 部分一致（高スコア）
            elif keyword_lower in features_lower:
                score += 1.0
            # 単語単位での部分一致（中スコア）
            elif any(word in features_lower for word in keyword_lower.split()):
                score += 0.5
            # 文字列の類似度（低スコア）
            else:
                # 文字列の類似度を計算
                similarity = self._calculate_string_similarity(features_lower, keyword_lower)
                if similarity > 0.7:  # 70%以上の類似度
                    score += similarity * 0.3
        
        return score / len(keywords) if keywords else 0.0
    
    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """文字列の類似度を計算（レーベンシュタイン距離ベース）"""
        if not str1 or not str2:
            return 0.0
        
        # 簡易的な類似度計算
        if str1 == str2:
            return 1.0
        
        # 共通文字数をカウント
        common_chars = set(str1) & set(str2)
        total_chars = set(str1) | set(str2)
        
        if not total_chars:
            return 0.0
        
        return len(common_chars) / len(total_chars)
    
    def _calculate_confidence(self, classification_result: Dict, features: str, detected_objects: List[Dict]) -> float:
        """分類結果の信頼度を計算"""
        base_confidence = classification_result.get("score", 0.0)
        
        # 物体検出による補正
        if detected_objects:
            max_object_confidence = max([obj["confidence"] for obj in detected_objects])
            object_bonus = max_object_confidence * 0.3
        else:
            object_bonus = 0.0
        
        # 特徴の豊富さによる補正
        feature_count = len(features.split(","))
        feature_bonus = min(feature_count * 0.05, 0.2)
        
        # 最終的な信頼度（0.0-1.0）
        confidence = min(base_confidence + object_bonus + feature_bonus, 1.0)
        
        return round(confidence, 2)
    
    def _get_fallback_result(self) -> Dict:
        """フォールバック結果を返す"""
        return {
            "large_category_id": "others",
            "large_category_name_ja": "その他",
            "medium_category_id": "items",
            "medium_category_name_ja": "その他",
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

    def suggest_category_by_name(self, item_name: str) -> Dict:
        try:
            if not item_name or not item_name.strip():
                logger.debug("空の品名が入力されました")
                return self._get_fallback_result()
            
            logger.debug(f"品名からの分類提案開始: {item_name}")

            # SemanticClassifierで推測
            suggestions = self.semantic_classifier.suggest_categories(item_name, top_n=1)
            if suggestions:
                best_term, score = suggestions[0]
                # best_term から大分類・中分類をitem_classification.jsonから逆引きする処理を追加
                # 例: self.classification_data から該当termを検索し、large_category_name_ja, medium_category_name_jaを取得
                for large in self.classification_data:
                    for medium in large.get("medium_categories", []):
                        for keyword in medium.get("keywords", []):
                            if keyword.get("term") == best_term:
                                return {
                                    "large_category": large["large_category_name_ja"],
                                    "medium_category": medium["medium_category_name_ja"],
                                    "name": item_name,
                                    "confidence": score
                                }
            # fallback
            return self._get_fallback_result()
        except Exception as e:
            logger.error(f"品名からの分類提案エラー: {e}")
            return self._get_fallback_result()
    
    def _extract_features_from_name(self, item_name: str) -> str:
        """品名から特徴を抽出"""
        features = []
        
        # 基本の品名
        features.append(f"品名: {item_name}")
        
        # 品名の長さによる特徴
        if len(item_name) <= 5:
            features.append("短い品名")
        elif len(item_name) <= 10:
            features.append("中程度の品名")
        else:
            features.append("長い品名")
        
        # 品名に含まれる可能性のある特徴を分析
        name_lower = item_name.lower()
        
        # 材質の特徴
        material_keywords = {
            "革": "革製", "皮": "革製", "leather": "革製",
            "布": "布製", "綿": "布製", "cotton": "布製",
            "金属": "金属製", "金": "金属製", "銀": "金属製", "metal": "金属製",
            "プラスチック": "プラスチック製", "plastic": "プラスチック製",
            "木": "木製", "wood": "木製", "竹": "竹製"
        }
        
        for keyword, material in material_keywords.items():
            if keyword in name_lower:
                features.append(material)
                break
        
        # 色の特徴
        color_keywords = {
            "黒": "黒色", "白": "白色", "赤": "赤色", "青": "青色", "緑": "緑色",
            "黄": "黄色", "紫": "紫色", "ピンク": "ピンク色", "オレンジ": "オレンジ色",
            "茶": "茶色", "グレー": "グレー色", "金": "金色", "銀": "銀色",
            "black": "黒色", "white": "白色", "red": "赤色", "blue": "青色"
        }
        
        for keyword, color in color_keywords.items():
            if keyword in name_lower:
                features.append(color)
                break
        
        # サイズの特徴
        size_keywords = {
            "小": "小型", "大": "大型", "中": "中型",
            "mini": "小型", "large": "大型", "small": "小型"
        }
        
        for keyword, size in size_keywords.items():
            if keyword in name_lower:
                features.append(size)
                break
        
        return ", ".join(features)

    def count_cash_from_image(self, image_path: str) -> Dict:
        """
        画像から日本の紙幣・硬貨の枚数を推定（ダミー実装）
        """
        # TODO: 本格的な画像認識ロジックを実装
        # 現時点ではダミーで全て0を返す
        return {
            "10000": 0,
            "5000": 0,
            "2000": 0,
            "1000": 0,
            "500": 0,
            "100": 0,
            "50": 0,
            "10": 0,
            "5": 0,
            "1": 0
        }

    def _build_classification_automaton(self):
        """正規表現パターンを構築"""
        keyword_map = []  # (pattern, payload, medium_category_id, orig_term)
        classification_data = self._load_classification_data()
        
        try:
            if isinstance(classification_data, list):
                # 新しい形式の分類データ（配列形式）
                for large_category in classification_data:
                    large_category_id = large_category.get("large_category_id", "")
                    large_category_name_ja = large_category.get("large_category_name_ja", "")
                    for medium_category in large_category.get("medium_categories", []):
                        medium_category_id = medium_category.get("medium_category_id", "")
                        medium_category_name_ja = medium_category.get("medium_category_name_ja", "")
                        priority = medium_category.get("priority", 0)
                        for keyword_data in medium_category.get("keywords", []):
                            # キーワードデータが辞書形式か文字列形式かを判定
                            if isinstance(keyword_data, dict):
                                term = keyword_data.get("term", "")
                                weight = keyword_data.get("weight", 1.0)
                            elif isinstance(keyword_data, str):
                                term = keyword_data
                                weight = 1.0
                            else:
                                continue
                            
                            if term:
                                payload = (
                                    large_category_id,
                                    large_category_name_ja,
                                    medium_category_id,
                                    medium_category_name_ja,
                                    weight,
                                    priority
                                )
                                normalized_term = self._normalize_text(term)
                                pattern = re.escape(normalized_term)
                                keyword_map.append((pattern, payload, medium_category_id, term))
            else:
                # 古い形式の分類データ（辞書形式）
                for category in classification_data.get("categories", []):
                    large_category = category.get("large_category", "")
                    for medium_category_data in category.get("medium_categories", []):
                        medium_category = medium_category_data.get("medium_category", "")
                        keywords = medium_category_data.get("keywords", [])
                        for keyword in keywords:
                            if isinstance(keyword, str) and keyword:
                                payload = (large_category, large_category, medium_category, medium_category, 1.0, 50)
                                normalized_term = self._normalize_text(keyword)
                                pattern = re.escape(normalized_term)
                                keyword_map.append((pattern, payload, medium_category, keyword))
        except Exception as e:
            logger.error(f"分類オートマトン構築エラー: {e}")
            # エラーが発生した場合は空のオートマトンを返す
            return (re.compile(""), [])
        
        if keyword_map:
            or_pattern = "|".join([p[0] for p in keyword_map])
            compiled_pattern = re.compile(or_pattern)
        else:
            compiled_pattern = re.compile("")
        return (compiled_pattern, keyword_map)
    
    def _normalize_text(self, text: str) -> str:
        """
        入力テキストを正規化する
        
        Args:
            text: 正規化するテキスト
            
        Returns:
            正規化されたテキスト
        """
        if not text:
            return ""
        # 1. 全角英数字記号を半角に
        text = mojimoji.zen_to_han(text, kana=False)
        
        #2文字に統一
        text = text.lower()
        
        # 3. カタカナの長音を削除
        text = text.replace("ー", "")
        
        # 4. その他の正規化ルール
        # ヴァ行の表記統一
        text = text.replace("ヴァ", "バ").replace("ヴィ", "ビ").replace("ヴェ", "ベ").replace("ヴォ", "ボ")
        
        # 濁点・半濁点の正規化（簡易的）
        text = text.replace("゛", "").replace("゜", "")
        
        # 空白文字の正規化
        text = " ".join(text.split())
        
        return text
    
    def classify_with_new_system(self, text: str) -> Dict:
        """
        新しい分類システムで品名から分類を決定論的に推測
        """
        if not text or not text.strip():
            return self._get_fallback_result()
        try:
            normalized_text = self._normalize_text(text)
            found_matches = []
            
            # 分類オートマトンが正しく構築されているかチェック
            if not self.classification_automaton or not self.classification_automaton[1]:
                logger.warning("分類オートマトンが正しく構築されていません")
                return self._get_fallback_result()
            
            # キーワードマッチング
            for pattern, payload, medium_category_id, orig_term in self.classification_automaton[1]:
                normalized_term = self._normalize_text(orig_term)
                if normalized_term in normalized_text:
                    # マッチした位置を計算
                    start_pos = normalized_text.find(normalized_term)
                    end_pos = start_pos + len(normalized_term)
                    found_matches.append((end_pos, payload, orig_term))
            
            if not found_matches:
                logger.debug(f"キーワードマッチが見つかりません: {text}")
                return self._get_fallback_result()
            
            best_match = self._select_best_match_new(found_matches, normalized_text)
            return {
                "large_category_id": best_match["large_category_id"],
                "large_category_name_ja": best_match["large_category_name_ja"],
                "medium_category_id": best_match["medium_category_id"],
                "medium_category_name_ja": best_match["medium_category_name_ja"],
                "confidence": best_match["confidence"],
                "matched_keywords": best_match["matched_keywords"]
            }
        except Exception as e:
            logger.error(f"新しい分類処理エラー: {e}")
            return self._get_fallback_result()
    
    def _select_best_match_new(self, matches: List[Tuple], text: str) -> Dict:
        """
        マッチした結果から最適な分類を選択（新しいシステム）
        
        Args:
            matches: マッチ結果 (end_pos, payload, orig_term)
            text: 正規化された入力テキスト
            
        Returns:
            最適な分類結果
        """
        # 中分類ごとのスコアを集計
        medium_category_scores = {}
        
        for end_index, (large_id, large_name, medium_id, medium_name, weight, priority), orig_term in matches:
            # キーワードの長さを取得（より長いキーワードを優先）
            keyword_length = len(orig_term)
            
            # スコア計算: 重み × キーワード長 × 優先度係数
            priority_factor = priority / 100.0  # 優先度を0-1の範囲に正規化
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
        
        # 最適な中分類を選択
        best_medium_id = max(
            medium_category_scores.keys(),
            key=lambda x: (
                medium_category_scores[x]["total_score"],
                medium_category_scores[x]["priority"]
            )
        )
        
        best_match = medium_category_scores[best_medium_id]
        
        # 信頼度を計算（0-1の範囲）
        max_possible_score = 10  # 理論上の最大スコア
        confidence = min(best_match["total_score"] / max_possible_score, 1.0)
        
        return {
            "large_category_id": best_match["large_category_id"],
            "large_category_name_ja": best_match["large_category_name_ja"],
            "medium_category_id": best_match["medium_category_id"],
            "medium_category_name_ja": best_match["medium_category_name_ja"],
            "confidence": round(confidence, 2),
            "matched_keywords": best_match["matched_keywords"]
        }
    
    def _get_keyword_length_at_position(self, text: str, end_index: int) -> int:
        """
        指定位置のキーワード長を取得
        
        Args:
            text: テキスト
            end_index: キーワードの終了位置
            
        Returns:
            キーワードの長さ
        """
        # マッチしたキーワードの長さを計算
        # 正規化されたテキストから元のキーワード長を推定
        if end_index <= 0:
            return 1
        
        # 簡易的な実装：マッチした部分の長さを返す
        # より正確な実装では、オートマトンから正確なキーワード長を取得する
        return min(end_index, len(text))
    
    def _get_keyword_at_position(self, text: str, end_index: int) -> str:
        """
        指定位置のキーワードを取得
        
        Args:
            text: テキスト
            end_index: キーワードの終了位置
            
        Returns:
            キーワード
        """
        # マッチしたキーワードを取得
        if end_index <= 0:
            return ""
        
        # 簡易的な実装：マッチした部分を返す
        # より正確な実装では、オートマトンから正確なキーワードを取得する
        return text[:end_index] if end_index <= len(text) else text
# グローバルAIエンジンインスタンス
ai_engine = AIEngine() 