# Lost Items Management System

## 概要

このプロジェクトは、AI技術を活用した拾得物管理システムです。
フロントエンドは「React + Electron」、バックエンドは「FastAPI（Python）」で構成されています。

---

## ディレクトリ構成

```
lost_items_desktop/
├── app/                # Pythonバックエンド（FastAPI）
├── backend/            # DBマイグレーション等
├── frontend/           # フロントエンド（React + Electron）
├── static/             # 静的ファイル（画像等）
├── requirements.txt    # Python依存パッケージ
├── README.md           # このファイル
└── .gitignore          # Git管理除外設定
```

---

## セットアップ手順（初回のみ）

### 1. Python（バックエンド）環境の準備

1. Python（バージョン3.8以上）をインストールしてください。
   - [Python公式サイト](https://www.python.org/downloads/)
2. コマンドプロンプトまたはPowerShellを開き、プロジェクトの`lost_items_desktop`フォルダに移動します。
   - 例：
     ```powershell
     cd C:\Users\ユーザー名\workspace\lost_items_desktop
     ```
3. 必要なPythonパッケージをインストールします。
   ```powershell
   pip install -r requirements.txt
   ```

### 2. Node.js（フロントエンド）環境の準備

1. Node.js（バージョン18以上推奨）をインストールしてください。
   - [Node.js公式サイト](https://nodejs.org/ja/download/)
2. コマンドプロンプトまたはPowerShellで`frontend`ディレクトリに移動します。
   ```powershell
   cd frontend
   ```
3. 必要なパッケージをインストールします。
   ```powershell
   npm install
   ```

---

## 開発用サーバーの起動方法

### 1. バックエンド（FastAPIサーバー）を起動

1. プロジェクトルートで`app`ディレクトリに移動します。
   ```powershell
   cd app
   ```
2. サーバーを起動します。
   ```powershell
   uvicorn main:app --reload
   ```
   - サーバーが起動したら、`http://localhost:8000` でAPIにアクセスできます。

### 2. フロントエンド（React開発サーバー）を起動

1. 新しいコマンドプロンプトまたはPowerShellを開き、`frontend`ディレクトリに移動します。
   ```powershell
   cd frontend
   ```
2. React開発サーバーを起動します。
   ```powershell
   npm start
   ```
   - ブラウザで `http://localhost:3000` を開くと、フロントエンド画面が表示されます。

---

## Electronアプリ（Windows用）のビルドと実行

1. `frontend`ディレクトリで以下のコマンドを順に実行します。
   ```powershell
   npm run build
   npm run build-exe
   ```
2. ビルドが完了すると、`frontend/dist/win-unpacked/` フォルダ内に `Lost Items Management System.exe` が生成されます。
3. この `.exe` ファイルをダブルクリックすると、デスクトップアプリとして起動します。

---

## 注意事項

- **ビルド成果物（dist, build, .exe, .asar等）はGit管理対象外です。**
  - これらは`.gitignore`で除外されています。
- **大容量ファイル（100MB超）はGitHubにpushできません。**
- **機密情報や個人情報はコミットしないでください。**
- **依存パッケージのインストールやサーバー起動時にエラーが出た場合は、エラーメッセージをよく読んで対処してください。**
- **コマンドはPowerShellやコマンドプロンプトで1行ずつ実行してください。**

---

## よくある質問（FAQ）

- **Q. コマンドが「認識されません」と出る場合は？**
  - → PythonやNode.jsのインストール、またはパス設定が正しいか確認してください。
- **Q. 依存パッケージのインストールでエラーが出る場合は？**
  - → インターネット接続や権限、バージョンを確認してください。
- **Q. サーバーやアプリが起動しない場合は？**
  - → エラーメッセージを確認し、不明な場合は開発者に相談してください。

---

## ライセンス

MIT License

---

## 開発・運用メモ

- バグ報告・要望はGitHubのIssueまたはPull Requestでお願いします。
- 詳細な設計や運用手順は`docs/`ディレクトリを参照してください。 