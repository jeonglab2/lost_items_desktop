---
version: 1.4
type: database-schema
---

# 04. データベーススキーマ
## Table: 'facilities' (施設認証テーブル)
|カラム名|データ型|制約|説明|
|---|---|---|---|
|'id'|SERIAL|PRIMARY KEY|施設ID (自動採番)|
|'facility_code'|VARCHAR(255)|UNIQUE, NOT NULL|施設コード (認証用)|
|'password_hash'|VARCHAR(255)|NOT NULL|ハッシュ化されたパスワード (Bcrypt)|
|'facility_name'|VARCHAR(255)|NOT NULL|施設名|
|'created_at'|TIMESTAMP WITH TIME ZONE|NOT NULL, DEFAULT 'now()'|作成日時|
|'updated_at'|TIMESTAMP WITH TIME ZONE|NOT NULL, DEFAULT 'now()'|更新日時|

## Table: 'items' (拾得物テーブル)
|カラム名|データ型|制約|説明|
|---|---|---|---|
|'item_id'|VARCHAR(255)|PRIMARY KEY|拾得物ID。'yy-mm-dd-h-nn'の形式 (yy-mm-ddは受付日, hは受付時の24時間形式の時刻, nnはその時間内の通し番号)。|
|'facility_id'|INTEGER|NOT NULL, FK -> 'facilities.id'|登録施設ID|
|'found_datetime'|TIMESTAMP WITH TIME ZONE|NOT NULL|拾得日時|
|'accepted_datetime'|TIMESTAMP WITH TIME ZONE|NOT NULL, DEFAULT 'now()'|受付日時|
|'found_place'|VARCHAR(255)|NOT NULL|拾得場所|
|'category_large'|VARCHAR(100)|NOT NULL|分類(大)。"eac_05_item_classification.json"に定義された値。|
|'category_medium'|VARCHAR(100)|NOT NULL|分類(中)。"eac_05_item_classification.json"に定義された値。|
|'name'|VARCHAR(255)|NOT NULL|品名|
|'features'|TEXT|NOT NULL|特徴|
|'color'|VARCHAR(50)|NOT NULL|色|
|'status'|VARCHAR(50)|NOT NULL, DEFAULT '保管中'|状態 ('保管中', '返還済', '警察届出済', '廃棄済')|
|'storage_location'|VARCHAR(255)|NOT NULL|保管場所。命名規則は下記の「ビジネスロジック」を参照。|
|'image_url'|VARCHAR(255)|NOT NULL|画像ファイルのURL|
|'finder_type'|VARCHAR(50)|NOT NULL|拾得者の属性 ('第三者', '施設占有者')|
|'claims_ownership'|BOOLEAN|NOT NULL, DEFAULT 'false'|拾得者が所有権を主張しているか|
|claims_reward|BOOLEAN|NOT NULL, DEFAULT 'false'|拾得者が報労金を請求しているか|
|'created_at'|TIMESTAMP WITH TIME ZONE|NOT NULL, DEFAULT 'now()'|作成日時|
|'updated_at'|TIMESTAMP WITH TIME ZONE|NOT NULL, DEFAULT 'now()'|更新日時|

## ビジネスロジックと命名規則 (Business Logic & Naming Conventions)
- 拾得物ID ('item_id')
    - フォーマット: 'yy-mm-dd-h-nn'
    - 生成ロジック: アプリケーション層で、受付日時を基に生成する。
        - 'yy-mm-dd': 受付日の年(下2桁)-月-日
        - 'h': 受付時の時間 (24時間形式)
        - 'nn': 同一時間内での2桁の通し番号 (例: 01, 02...)
- 保管場所 ('storage_location') の提案ロジック (優先度順)
    1. 所有権が主張されている物品:
        - ID: 'yy-mm-dd-所有権主張'
        - 条件: 'claims_ownership'が'true'の場合に提案される。
    2. 傘:
        - ID: 'yy-mm-dd-umb'
        - 条件: 品名が「傘」の場合に提案される。
    3. 食品 (要冷蔵・冷凍):
        - 冷蔵庫ID: 'yy-mm-dd-冷蔵庫'
        - 冷凍庫ID: 'yy-mm-dd-冷凍庫'
        - 条件: 特徴に「食品」が含まれる場合に提案される。
    4. デフォルトの保管場所:
        - フォーマット: 'yy-mm-dd-nn'
        - ロジック:
            - 'yy-mm-dd': 受付日の年(下2桁)-月-日
            - 'nn': 保管箱の2桁の通し番号。この番号は、同一受付日の拾得物が20個登録されるごとにインクリメントされる (例: 1〜20個目は'01', 21〜40個目は'02')。
- 7日後の保管場所更新ロジック
    - トリガー: 受付日から7日経過した物品に対して、バッチ処理などで自動更新する。
    - 新フォーマット: 'yy-mm-dd-nn-nn'
    - ロジック:
        - 'yy-mm-dd': 拾得日の年(下2桁)-月-日
        - 'nn-nn': 初期登録時に割り当てられた保管箱の通し番号を繰り返す (例: '01'なら'01-01')。
    - 注意: 特殊な保管場所（所有権主張、傘立て、冷蔵庫、冷凍庫）は、この更新ロジックの対象外とする。

### Indexes for 'items' table:
- 'CREATE INDEX ON items (facility_id, created_at DESC);'
- 'CREATE INDEX ON items (facility_id, status);'
- 'CREATE INDEX ON items (facility_id, category_large, category_medium);'
- 'CREATE EXTENSION IF NOT EXISTS pg_trgm; CREATE INDEX ON items USING gin (name gin_trgm_ops, features gin_trgm_ops);' (全文検索用)

### Table: 'audit_logs' (監査ログテーブル)
|カラム名|データ型|制約|説明|
|---|---|---|---|
|'id'|BIGSERIAL|PRIMARY KEY|ログID (自動採番)|
|'log_timestamp'|TIMESTAMP WITH TIME ZONE|NOT NULL, DEFAULT 'now()'|操作日時|
|'facility_id'|INTEGER|FK -> 'facilities.id'|操作を行った施設ID|
|'user_id'|INTEGER| |操作を行った担当者ID (将来用)|
|'action_type'|VARCHAR(50)|NOT NULL|操作種別 ('CREATE', 'UPDATE', 'DELETE')|
|'target_table'|VARCHAR(100)|NOT NULL|操作対象テーブル名 (e.g., 'items')|
|'target_id'|VARCHAR(255)|NOT NULL|操作対象レコードのID (items.item_idなど)|
|'details'|JSONB| |変更内容の詳細 (変更前後の値など)|