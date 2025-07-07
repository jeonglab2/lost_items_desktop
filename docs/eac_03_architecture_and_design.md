---
version: 1.1
type: architecture-design
---

# 03. アーキテクチャとAPI設計
## 1. 技術アーキテクチャ
- Frontend: デスクトップアプリケーション (Electron, React, TypeScriptなどを想定)
- Backend: APIサーバー (Python, FastAPIなどを想定)
- Database: リレーショナルデータベース (PostgreSQLなどを想定)
- AI Engine: 画像認識モデルをホストする推論サーバー (クラウドGPU VRAM 8GB以上を推奨)。分類推論の知識ベースとしてeac_05_item_classification.jsonを利用する。
- Deployment: コンテナ技術 (Docker) を利用し、CI/CDパイプラインを構築する。

## 2. 画面設計 (Screen Design)
### SCR-03: 拾得物登録画面
- Layout: 2カラムレイアウト（左: 画像エリア, 右: 入力フォーム）
- Components:
  - 画像エリア:
    - Webカメラ映像表示
    - [撮影] ボタン
    - [画像ファイルを選択] ボタン
    - プレビュー表示
    - 注釈: ※画像は後からでも登録できます
  - 入力フォーム:
    - 拾得日時/受付日時 (Date/Time Picker)
    - 拾得場所 (Text Input)
    - 分類 (大/中) (Dropdown, AI提案)
    - 品名 (Text Input, AI提案)
    - 特徴 (Text Area, AI提案)
    - 色 (Text Input, AI提案)
    - 確信度表示: AI提案項目の横に (98%) のように表示。担当者が値を変更すると非表示になる。
    - [登録] ボタン, [クリア] ボタン

## 3. API設計 (API Design)
### Endpoint: POST /api/v1/recognize
- Description: 画像を解析し、拾得物の情報を抽出する。
- Request:
  - Headers: Content-Type: multipart/form-data
  - Body: image: 画像ファイル
- Response (Success: 200 OK):
{
  "success": true,
  "data": {
    "category_large": {"value": "かばん類", "confidence": 0.98},
    "category_medium": {"value": "手提げかばん", "confidence": 0.95},
    "name": {"value": "ハンドバッグ", "confidence": 0.88},
    "features": {"value": "革製、茶色、ゴールドの金具", "confidence": 0.92},
    "color": {"value": "茶", "confidence": 0.99},
    "storage_location_suggestion": {"value": "25-06-20-01", "confidence": 0.85},
    "bounding_box": [10, 45, 150, 200]
  }
}
- Error Handling:
  - 400 Bad Request: 画像形式が不正な場合
  - 429 Too Many Requests: レート制限超過 (1分あたり60回)
  - 503 Service Unavailable: AIエンジンが利用不可の場合

### Endpoint: POST /api/v1/auth/token
- Description: 施設認証を行い、トークンを発行する。
- Request:
{
  "facility_code": "your_facility_code",
  "password": "your_password"
}
- Response (Success: 200 OK):
{
  "access_token": "ey...",
  "refresh_token": "ey...",
  "token_type": "bearer"
}
(その他のAPI: /refresh, /revoke なども同様に定義)
