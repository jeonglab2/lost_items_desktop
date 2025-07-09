新規拾得物管理システム実装プロンプト

# 1. プロジェクトの目的
これから、AIを活用した「新規拾得物管理システム」を構築します。このシステムは、商業施設などでの拾得物管理業務を効率化し、精度を向上させることを目的としています。

すべての要件と仕様は、後述する`eac`（Everything as Code）ドキュメント群に定義されています。これらのドキュメントを正として、開発を進めてください。

# 2. 実装の進め方
以下のステップで開発を進めます。各ステップでは、関連するeacドキュメントを参照してください。

## Step 1: バックエンド (APIサーバー) の構築
技術スタック: Python, FastAPI, PostgreSQL (推奨)

1. データベースのセットアップ:
    - "eac_04_database_schema.md" に基づき、PostgreSQLにテーブル、インデックス、制約を作成してください。
    - データベースのマイグレーションツール（Alembicなど）を導入してください。
2. APIエンドポイントの実装:
    - "eac_03_architecture_and_design.md" に定義されたAPI仕様（`/recognize`, `/auth/token`など）をFastAPIで実装してください。
    - ORM（SQLAlchemyなど）を使用して、データベースとのやり取りを実装します。
3. ビジネスロジックの実装:
    - "eac_04_database_schema.md"の「ビジネスロジックと命名規則」セクションに基づき、以下のロジックを実装してください。
        - 拾得物ID (`item_id`) の自動生成ロジック。
        - 保管場所 (`storage_location`) の提案・更新ロジック。

## Step 2: AIエンジン の構築
技術スタック: Python, PyTorch/TensorFlow, ONNX (推奨)

1. 画像認識モデルの準備:
    - 拾得物の画像を解析し、品名、特徴、色などを抽出できる画像認識モデル（物体検出・分類モデル）を準備します。
2. 分類ロジックの実装:
    - AIモデルの分類知識ベースとして、"eac_05_item_classification.json" を読み込み、活用してください。
    - 画像から抽出した特徴と、"eac_05_item_classification.json" の`keywords`を照合し、最も確からしい「大分類」「中分類」を特定するロジックを実装します。
3. セマンティック検索のためのベクトル生成:
    - "eac_01_functional_requirements.md" の検索要件を満たすため、登録された拾得物の「品名」「特徴」テキストから、Sentence Transformerなどを用いてベクトル（embeddings）を生成し、データベースに保存する仕組みを実装してください。（DBスキーマに`vector`カラムを追加する必要があります）

## Step 3: フロントエンド (デスクトップアプリ) の構築
技術スタック: Electron, React, TypeScript, Tailwind CSS (推奨)

1. UIコンポーネントの実装:
    - "eac_03_architecture_and_design.md" の「画面設計」に基づき、Reactコンポーネントを作成してください。特に「拾得物登録画面」のレイアウトとインタラクションを正確に実装します。
2. API連携:
    - 作成したバックエンドAPIと通信し、データの取得、登録、更新処理を実装してください。
3. 機能要件の実装:
    - "eac_01_functional_requirements.md" に記述されたユーザーストーリーとAcceptance Criteriaを満たすように、各機能を実装してください。
    - 特に、AIによる分類・保管場所の提案、権利情報の入力、高度な検索機能（絞り込み、結果表示）を重点的に実装します。

## Step 4: 全体の統合とテスト
1. 非機能要件の確認:
    - "eac_02_non_functional_requirements.md" に記載された性能、セキュリティ、信頼性などの要件を満たしているか確認し、必要な対策を講じてください。
2. CI/CDパイプラインの構築:
    - GitHub Actionsなどを利用して、テストとデプロイを自動化するパイプラインを構築してください。

# 3. AI用リファレンスドキュメント
開発に必要なすべてのドキュメントを以下に添付します。

## 3.1. "eac_00_project_overview.md"
```
---
version: 1.0
type: project-overview
system_name: 新規拾得物管理システム
---

# 00. プロジェクト全体像

## 1. プロジェクトの目的 (Purpose)

本プロジェクトは、AI技術を活用して拾得物管理業務を革新し、以下の価値を提供することを目的とする。

- **業務効率の大幅な向上**: 登録・検索業務の自動化・省力化。
- **管理精度の向上**: 人的ミスや主観を排除した、客観的で一貫性のあるデータ管理の実現。
- **リアルタイムな情報共有**: 施設内の複数拠点における、迅速な情報アクセス環境の構築。

## 2. 主要成功指標 (KPIs)

| 指標ID | 項目 | 目標値 | 備考 |
| :--- | :--- | :--- | :--- |
| KPI-01 | 拾得物登録時間/件 | 1分以内 | 従来比66%以上の工数削減を目指す。 |
| KPI-02 | 検索応答時間 | 2秒以内 (95パーセンタイル) | ユーザー体験を考慮した明確な性能目標。 |
| KPI-03 | AI分類精度(中分類) | F1スコア 0.9以上 | 評価指標を明確化し、ビジネスインパクトを評価する。 |
| KPI-04 | システム受容度 | 利用者満足度アンケートで平均4.0/5.0以上 | 導入後3ヶ月時点で測定。システムの定着度を測る。 |

## 3. 開発ロードマップ (Roadmap)

| フェーズ | 名称 | 主要目標 |
| :--- | :--- | :--- |
| 1st Gen | 基盤システムの構築と実証 | 堅牢なデスクトップアプリケーションを完成させ、現行ソフトウェアを代替する。 |
| 2nd Gen | アプリケーション化とビジネスモデル変革 | サブスクリプション型(SaaS)のWeb/モバイルアプリケーションへ進化させる。 |
| 3rd Gen | CtoCプラットフォームへの展開 | 拾得者と遺失者が直接やり取りできるプラットフォームを構築する。 |
```


## 3.2. "eac_01_functional_requirements.md"

```
---
version: 1.4
type: functional-requirements
---

# 01. 機能要件

## Epic: 拾得物の登録 (Item Registration)

### FR-01-01: AIによる自動入力とインテリジェントな分類・提案
- **As a** 施設担当者,
- **I want to** 拾得物の情報が、物品の特性や法的要件に応じて賢く分類・提案され、簡単に入力できるようにしてほしい,
- **so that** 手入力の手間を省き、遺失物法に則った適切な管理を、一貫性を持って実現したい。
- **Acceptance Criteria**:
    - [ ] 写真をアップロードすると、AIが解析を開始する。
    - [ ] **分類提案**: AIは、`eac_05_item_classification.json`を知識ベースとして、拾得物の大分類・中分類を提案する。
    - [ ] 解析結果（品名、特徴など）が登録フォームの各項目に自動で入力される。
    - [ ] AIの提案には確信度(Confidence Score)がパーセンテージで併記される。
    - [ ] **権利情報の入力**:
        - [ ] 「拾得者の属性」を「第三者」「施設占有者」から選択できる。
        - [ ] 「所有権の主張」の有無をチェックボックス等で選択できる。
        - [ ] 「報労金の請求権」の有無をチェックボックス等で選択できる。
    - [ ] **保管場所の提案ロジック (優先度順)**:
        1.  **[最優先]** 「所有権の主張」が「有り」の場合、保管場所に「yy-mm-dd-所有権主張」を自動で提案する。
        2.  AIが品名を「傘」と判断した場合、保管場所に「yy-mm-dd-umb」を自動で提案する。
        3.  AIが特徴に「食品」が含まれると判断した場合、保管場所に「yy-mm-dd-冷蔵庫」または「yy-mm-dd-冷凍庫」を自動で提案する。
        4.  上記以外の場合は、デフォルトの保管場所命名規則「yy-mm-dd-nn」に従って提案する。
    - [ ] **手動入力のサポート**:
        - [ ] 分類や保管場所の入力フィールドは、ドロップダウンリスト形式になっている。
        - [ ] 分類のドロップダウンリストには`eac_05_item_classification.json`に基づいた選択肢が表示される。
    - [ ] 担当者はAIの提案内容や権利情報を修正できる。
    - [ ] 画像を登録せずに、テキスト情報のみで登録することも可能である。

## Epic: 拾得物の検索 (Item Search)

### FR-02-01: 高度な検索機能 (Advanced Search)
- **As a** 施設担当者,
- **I want to** 品名、特徴などのキーワードや、拾得場所・日付で、登録された拾得物を柔軟かつ正確に検索したい,
- **so that** 遺失者からの「黒っぽい上着」のような曖昧な情報からでも迅速に対応できる。
- **Acceptance Criteria**:
    - [ ] **セマンティック検索**: 「ジャケット」で検索した場合、「上着」や「ジャンパー」など、意味的に関連する物品も検索結果に含まれる。AIがテキストの特徴量をベクトル化し、検索クエリとの類似度に基づいて結果をランキングする。
    - [ ] **キーワード検索**: 複数のキーワードを組み合わせてAND検索ができる。
    - [ ] **絞り込み**: 検索結果を拾得場所（テキスト入力）や拾得日の期間（開始日・終了日）で絞り込める。
    - [ ] **結果表示**: 検索結果は一覧で表示され、写真のサムネイルも確認できる。

## Epic: 拾得物の管理 (Item Management)
... (以下略) ...
```

## 3.3. "eac_02_non_functional_requirements.md"
```
---
version: 1.0
type: non-functional-requirements
---

# 02. 非機能要件

## NFR-PERF: 性能・スケーラビリティ
- **NFR-PERF-01**: 検索応答時間は、95パーセンタイルのリクエストにおいて2秒以内に完了すること。
- **NFR-PERF-02**: 通常時10名、ピーク時30名の同時接続ユーザーの負荷に耐えること。
... (以下略) ...
```

## 3.4. "eac_03_architecture_and_design.md"
```
---
version: 1.1
type: architecture-design
---

# 03. アーキテクチャとAPI設計

## 1. 技術アーキテクチャ
- **Frontend**: デスクトップアプリケーション (Electron, React, TypeScriptなどを想定)
- **Backend**: APIサーバー (Python, FastAPIなどを想定)
- **Database**: リレーショナルデータベース (PostgreSQLなどを想定)
- **AI Engine**: 画像認識モデルをホストする推論サーバー (クラウドGPU VRAM 8GB以上を推奨)。分類推論の知識ベースとして`eac_05_item_classification.json`を利用する。
- **Deployment**: コンテナ技術 (Docker) を利用し、CI/CDパイプラインを構築する。

## 2. 画面設計 (Screen Design)
... (以下略) ...

## 3. API設計 (API Design)
... (以下略) ...
```

## 3.5. "eac_04_database_schema.md"
```
---
version: 1.4
type: database-schema
---

# 04. データベーススキーマ

## Table: `items` (拾得物テーブル)

| カラム名 | データ型 | 制約 | 説明 |
| :--- | :--- | :--- | :--- |
| `item_id` | VARCHAR(255) | PRIMARY KEY | 拾得物ID。`yy-mm-dd-h-nn`の形式。 |
| `facility_id` | INTEGER | NOT NULL, FK -> `facilities.id` | 登録施設ID |
| `category_large` | VARCHAR(100) | | 分類(大)。`eac_05_item_classification.json`に定義された値。 |
| `category_medium` | VARCHAR(100) | | 分類(中)。`eac_05_item_classification.json`に定義された値。 |
| `claims_ownership`| BOOLEAN | NOT NULL, DEFAULT `false` | 拾得者が所有権を主張しているか |
| `claims_reward` | BOOLEAN | NOT NULL, DEFAULT `false` | 拾得者が報労金を請求しているか |
... (以下略) ...

### ビジネスロジックと命名規則 (Business Logic & Naming Conventions)
... (以下略) ...
```

## 3.6. "eac_05_item_classification.json"
```
{
  "version": "1.0",
  "description": "拾得物の分類定義ファイル。AIが品名や特徴から適切な分類を推論するために使用します。",
  "categories": [
    {
      "large_category": "かばん類",
      "medium_categories": [
        {
          "medium_category": "手提げかばん",
          "keywords": ["ハンドバッグ", "ビジネスバッグ", "トートバッグ", "ボストンバッグ", "アタッシュケース", "トランク", "学生かばん", "ブリーフケース", "handbag", "tote bag", "business bag"]
        },
... (以下略) ...
      ]
    }
  ]
}
```

# 4 既存のhtml形式のプロトタイプ
## "lost_and_found_prottype_1.html"
GUIデザインの参考として使用すること。
```
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>拾得物管理システム プロトタイプ v5.0</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+JP:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
... (以下略) ...
    </style>
</head>

<body class="bg-gray-100 flex items-center justify-center min-h-screen">
... (以下略) ...
</body>

<script>
... (以下略) ...
</script>
</html>

```
