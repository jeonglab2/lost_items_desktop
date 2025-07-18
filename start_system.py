#!/usr/bin/env python3
"""
拾得物管理システム 起動スクリプト
"""

import os
import sys
import subprocess
import time
import signal
import threading
from pathlib import Path

class SystemStarter:
    def __init__(self):
        self.processes = []
        self.running = True
        
    def setup_environment(self):
        """環境設定"""
        print("環境設定を開始します...")
        
        # ログディレクトリ作成
        Path("logs").mkdir(exist_ok=True)
        
        # 環境変数設定
        os.environ.setdefault("DATABASE_URL", "postgresql://postgres:admin123@localhost:5432/lost_items")
        os.environ.setdefault("SECRET_KEY", "your-secret-key-here")
        
        print("環境設定完了")
    
    def check_dependencies(self):
        """依存関係チェック"""
        print("依存関係をチェックしています...")
        
        required_packages = [
            ("fastapi", "fastapi"),
            ("uvicorn", "uvicorn"),
            ("sqlalchemy", "sqlalchemy"),
            ("psycopg2-binary", "psycopg2"),
            ("torch", "torch"),
            ("transformers", "transformers"),
            ("ultralytics", "ultralytics"),
            ("easyocr", "easyocr")
        ]
        
        missing_packages = []
        for pip_name, import_name in required_packages:
            try:
                __import__(import_name)
            except ImportError:
                missing_packages.append(pip_name)
        
        if missing_packages:
            print(f"不足しているパッケージ: {missing_packages}")
            print("以下のコマンドでインストールしてください:")
            print(f"pip install {' '.join(missing_packages)}")
            return False
        
        print("依存関係チェック完了")
        return True
    
    def setup_database(self):
        """データベースセットアップ"""
        print("データベースをセットアップしています...")
        
        try:
            # Alembicマイグレーション実行
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                cwd="backend",
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("データベースマイグレーション完了")
            else:
                print(f"マイグレーション警告: {result.stderr}")
                
        except FileNotFoundError:
            print("Alembicが見つかりません。手動でマイグレーションを実行してください。")
    
    def download_ai_models(self):
        """AIモデルのダウンロード"""
        print("AIモデルをダウンロードしています...")
        
        try:
            # YOLOモデルのダウンロード
            from ultralytics import YOLO
            model = YOLO('backend/yolov8n.pt')
            print("YOLOモデルダウンロード完了")
            
            # EasyOCRモデルのダウンロード
            import easyocr
            reader = easyocr.Reader(['ja', 'en'])
            print("EasyOCRモデルダウンロード完了")
            
        except Exception as e:
            print(f"AIモデルダウンロード警告: {e}")
    
    def start_backend(self):
        """バックエンドサーバー起動"""
        print("バックエンドサーバーを起動しています...")
        
        try:
            # ルートディレクトリから起動（appディレクトリがルートにあるため）
            root_dir = Path(".").absolute()
            process = subprocess.Popen([
                sys.executable, "-m", "uvicorn", "app.main:app",
                "--host", "0.0.0.0", "--port", "8000", "--reload"
            ], cwd=root_dir)
            self.processes.append(("Backend", process))
            print("バックエンドサーバー起動完了 (http://localhost:8000)")
            
        except Exception as e:
            print(f"バックエンド起動失敗: {e}")
    
    def start_frontend(self):
        """フロントエンドサーバー起動"""
        print("フロントエンドサーバーを起動しています...")
        
        try:
            # フロントエンドディレクトリのパスを取得
            frontend_dir = Path("frontend").absolute()
            
            # ディレクトリが存在するか確認
            if not frontend_dir.exists():
                print(f"フロントエンドディレクトリが見つかりません: {frontend_dir}")
                return
            
            # package.jsonが存在するか確認
            if not (frontend_dir / "package.json").exists():
                print(f"package.jsonが見つかりません: {frontend_dir / 'package.json'}")
                return
            
            # npmコマンドのパスを確認
            npm_path = None
            try:
                # まずnpmコマンドを直接試行
                result = subprocess.run(["npm", "--version"], capture_output=True, text=True)
                if result.returncode == 0:
                    npm_path = "npm"
                    print(f"npm version: {result.stdout.strip()}")
            except FileNotFoundError:
                # npmが見つからない場合、Node.jsのインストールパスを探す
                possible_npm_paths = [
                    r"C:\Program Files\nodejs\npm.cmd",
                    r"C:\Program Files (x86)\nodejs\npm.cmd",
                    os.path.expanduser(r"~\AppData\Roaming\npm\npm.cmd"),
                    os.path.expanduser(r"~\AppData\Local\Programs\nodejs\npm.cmd")
                ]
                
                for path in possible_npm_paths:
                    if os.path.exists(path):
                        npm_path = path
                        print(f"npm found at: {npm_path}")
                        break
                
                if not npm_path:
                    print("npmが見つかりません。Node.jsがインストールされているか確認してください。")
                    return
            
            # 依存関係インストール（初回のみ）
            if not (frontend_dir / "node_modules").exists():
                print("フロントエンド依存関係をインストールしています...")
                subprocess.run([npm_path, "install"], cwd=frontend_dir, check=True)
            
            # 開発サーバー起動
            process = subprocess.Popen([npm_path, "start"], cwd=frontend_dir)
            self.processes.append(("Frontend", process))
            print("フロントエンドサーバー起動完了 (http://localhost:3000)")
            
        except Exception as e:
            print(f"フロントエンド起動失敗: {e}")
            import traceback
            traceback.print_exc()
    
    def monitor_processes(self):
        """プロセス監視"""
        while self.running:
            for name, process in self.processes:
                if process.poll() is not None:
                    print(f"{name}プロセスが終了しました (終了コード: {process.returncode})")
            time.sleep(5)
    
    def signal_handler(self, signum, frame):
        """シグナルハンドラー"""
        print("\nシステムを停止しています...")
        self.running = False
        
        for name, process in self.processes:
            print(f"停止中: {name}")
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    process.kill()
                except:
                    pass
            except Exception as e:
                print(f"{name}停止エラー: {e}")
        
        print("システム停止完了")
        # 非同期処理のキャンセルエラーを無視して終了
        try:
            sys.exit(0)
        except:
            os._exit(0)
    
    def start_system(self):
        """システム全体を起動"""
        print("拾得物管理システムを起動します...")
        print("=" * 50)
        
        # シグナルハンドラー設定
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # 環境設定
        self.setup_environment()
        
        # 依存関係チェック
        if not self.check_dependencies():
            sys.exit(1)
        
        # データベースセットアップ
        self.setup_database()
        
        # AIモデルダウンロード
        self.download_ai_models()
        
        # バックエンド起動
        self.start_backend()
        
        # 少し待ってからフロントエンド起動
        time.sleep(3)
        self.start_frontend()
        
        # プロセス監視開始
        monitor_thread = threading.Thread(target=self.monitor_processes, daemon=True)
        monitor_thread.start()
        
        print("=" * 50)
        print("システム起動完了!")
        print("フロントエンド: http://localhost:3000")
        print("バックエンドAPI: http://localhost:8000")
        print("APIドキュメント: http://localhost:8000/docs")
        print("=" * 50)
        print("停止するには Ctrl+C を押してください")
        
        # メインループ
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.signal_handler(signal.SIGINT, None)

def main():
    """メイン関数"""
    starter = SystemStarter()
    starter.start_system()

if __name__ == "__main__":
    main() 