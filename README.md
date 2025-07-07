# 拾得物管理システム

AI技術を活用した拾得物管理システムです。画像認識、セマンティック検索、自動分類機能により、拾得物の登録・検索・管理を効率化します。

## 🚀 主な機能

### 拾得物登録
- **AI画像認識**: 写真をアップロードすると自動で品名・特徴・色を認識
- **自動分類**: 拾得物の大分類・中分類を自動提案
- **保管場所提案**: 所有権主張や品目に応じた保管場所を自動提案
- **権利情報管理**: 拾得者の属性、所有権主張、報労金請求権の管理

### 拾得物検索
- **セマンティック検索**: 意味的に類似する物品も検索結果に含める
- **キーワード検索**: 複数キーワードによるAND検索
- **絞り込み機能**: 拾得場所・日付範囲での絞り込み
- **結果表示**: サムネイル付き一覧表示

### 拾得物管理
- **保管期限管理**: 期限切れ・期限間近アイテムの自動検出
- **統計表示**: 保管状況の統計情報
- **一括操作**: 複数アイテムの一括更新・削除

## 🏗️ アーキテクチャ

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   フロントエンド   │    │    バックエンド    │    │   AIエンジン     │
│   (React/TS)    │◄──►│   (FastAPI)     │◄──►│  (YOLO/OCR)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   データベース    │
                       │  (PostgreSQL)   │
                       └─────────────────┘
```

## 📋 システム要件

### 必須要件
- Python 3.9+
- Node.js 16+
- PostgreSQL 13+
- 8GB RAM以上
- 10GB以上の空き容量

### 推奨要件
- GPU (NVIDIA CUDA対応)
- 16GB RAM以上
- SSDストレージ

## 🛠️ セットアップ

### 1. リポジトリのクローン
```bash
git clone <repository-url>
cd lost_items_desktop
```

### 2. 環境構築

#### WSL (Windows Subsystem for Linux) の場合
```bash
# conda環境の作成
conda create -n lost_items python=3.9
conda activate lost_items

# 依存関係のインストール
pip install -r requirements.txt

# データベースのセットアップ
cd backend
alembic upgrade head
cd ..

# AIモデルの事前ダウンロード
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
python -c "import easyocr; easyocr.Reader(['ja', 'en'])"
```

#### フロントエンドのセットアップ
```bash
cd frontend
npm install
cd ..
```

### 3. 環境変数の設定
```bash
# .envファイルを作成
cat > .env << EOF
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/lost_items
SECRET_KEY=your-secret-key-here
EOF
```

### 4. システム起動

#### 自動起動（推奨）
```bash
python start_system.py
```

#### 手動起動
```bash
# バックエンド起動
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 別ターミナルでフロントエンド起動
cd frontend
npm start
```

## 🧪 テスト実行

```bash
# 全テスト実行
pytest tests/ -v

# カバレッジ付きテスト
pytest tests/ --cov=app --cov-report=html

# セキュリティスキャン
bandit -r app/
safety check
```

## 📚 API ドキュメント

システム起動後、以下のURLでAPIドキュメントを確認できます：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔒 セキュリティ機能

- **認証**: JWTトークンベース認証
- **パスワード**: Bcryptハッシュ化
- **ファイル検証**: MIMEタイプ・サイズ制限・マルウェアスキャン
- **入力サニタイズ**: XSS・SQLインジェクション対策
- **監査ログ**: 全操作のログ記録

## 📊 監視・ログ

### ログファイル
- `logs/application.log`: アプリケーションログ
- `logs/audit.log`: 監査ログ

### 監視項目
- API応答時間（2秒以内）
- AI処理時間（10秒以内）
- データベース接続状況
- エラー発生率

## 🚀 デプロイ

### Docker を使用したデプロイ
```bash
# イメージビルド
docker build -t lost-items-system .

# コンテナ起動
docker run -p 8000:8000 lost-items-system
```

### CI/CD パイプライン
GitHub Actionsを使用した自動テスト・デプロイパイプラインが設定されています：

- **テスト**: 自動テスト実行
- **セキュリティスキャン**: 脆弱性チェック
- **コード品質**: リント・フォーマットチェック
- **デプロイ**: ステージング・本番環境への自動デプロイ

## 📈 パフォーマンス

### 目標値
- **検索応答時間**: 2秒以内（95パーセンタイル）
- **同時接続ユーザー**: 通常時10名、ピーク時30名
- **AI分類精度**: F1スコア 0.9以上
- **システム稼働率**: 99.9%

### 最適化
- データベースインデックス最適化
- AIモデルのキャッシュ
- 画像の圧縮・リサイズ
- 非同期処理の活用

## 🤝 開発者向け情報

### ディレクトリ構造
```
lost_items_desktop/
├── app/                    # バックエンドアプリケーション
│   ├── main.py            # FastAPIアプリケーション
│   ├── ai_engine.py       # AIエンジン
│   ├── database.py        # データベース設定
│   ├── models.py          # データモデル
│   ├── security.py        # セキュリティ機能
│   └── logging_config.py  # ログ設定
├── frontend/              # フロントエンドアプリケーション
│   ├── src/
│   │   ├── screens/       # 画面コンポーネント
│   │   └── App.tsx        # メインアプリケーション
│   └── package.json
├── backend/               # データベース関連
│   ├── alembic/          # マイグレーション
│   └── alembic.ini
├── docs/                 # ドキュメント
├── tests/                # テストコード
└── requirements.txt      # Python依存関係
```

### 開発ガイドライン
- **コード品質**: Black、isort、flake8、mypyを使用
- **テスト**: pytestでユニットテスト・統合テストを実装
- **セキュリティ**: OWASP Top 10対策を実装
- **ドキュメント**: APIドキュメントを自動生成

## 📞 サポート

### トラブルシューティング
1. **ログ確認**: `logs/application.log`を確認
2. **依存関係チェック**: `pip list`でパッケージ確認
3. **データベース接続**: PostgreSQLの起動確認
4. **AIモデル**: モデルファイルの存在確認

### よくある問題
- **メモリ不足**: AIモデルの読み込みに失敗する場合
- **GPU未対応**: CPUモードで動作（処理時間が長くなる）
- **データベース接続エラー**: PostgreSQLの起動・認証設定確認

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🙏 謝辞

- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics)
- [EasyOCR](https://github.com/JaidedAI/EasyOCR)
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://reactjs.org/)

---

**開発チーム**: 拾得物管理システム開発チーム  
**バージョン**: 1.0.0  
**最終更新**: 2024年1月 