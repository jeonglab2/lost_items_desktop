import bcrypt
import jwt
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
import logging
import re
from pathlib import Path
import mimetypes
import os

logger = logging.getLogger(__name__)

class SecurityManager:
    def __init__(self, secret_key: str = None):
        """セキュリティマネージャーの初期化"""
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 90
        
        # 許可されるファイル形式
        self.allowed_mime_types = {
            'image/jpeg', 'image/png', 'image/gif', 'image/webp'
        }
        
        # ファイルサイズ制限（10MB）
        self.max_file_size = 10 * 1024 * 1024
        
        # 危険なファイルパターン
        self.dangerous_patterns = [
            r'\.(exe|bat|cmd|com|pif|scr|vbs|js|jar|msi|dll|sys)$',
            r'<script',
            r'javascript:',
            r'vbscript:',
            r'data:text/html',
            r'data:application/x-javascript'
        ]
    
    def hash_password(self, password: str) -> str:
        """パスワードをハッシュ化"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """パスワードを検証"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """アクセストークンを生成"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """リフレッシュトークンを生成"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """トークンを検証"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.JWTError:
            logger.warning("Invalid token")
            return None
    
    def validate_file_upload(self, file_path: str, file_size: int) -> Dict[str, Any]:
        """ファイルアップロードの検証"""
        result = {
            "valid": True,
            "message": "OK",
            "mime_type": None
        }
        
        # ファイルサイズチェック
        if file_size > self.max_file_size:
            result["valid"] = False
            result["message"] = f"ファイルサイズが大きすぎます（最大{self.max_file_size // (1024*1024)}MB）"
            return result
        
        # MIMEタイプチェック
        try:
            mime_type, _ = mimetypes.guess_type(file_path)
            result["mime_type"] = mime_type
            
            if mime_type not in self.allowed_mime_types:
                result["valid"] = False
                result["message"] = f"許可されていないファイル形式です: {mime_type}"
                return result
        except Exception as e:
            logger.error(f"MIME type detection failed: {e}")
            result["valid"] = False
            result["message"] = "ファイル形式の検証に失敗しました"
            return result
        
        # 危険なパターンチェック
        file_name = Path(file_path).name.lower()
        for pattern in self.dangerous_patterns:
            if re.search(pattern, file_name, re.IGNORECASE):
                result["valid"] = False
                result["message"] = "危険なファイル名が検出されました"
                return result
        
        return result
    
    def sanitize_input(self, text: str) -> str:
        """入力テキストのサニタイズ"""
        if not text:
            return text
        
        # HTMLタグの除去
        text = re.sub(r'<[^>]+>', '', text)
        
        # 危険な文字列の除去
        dangerous_strings = [
            'javascript:', 'vbscript:', 'data:text/html', 
            'data:application/x-javascript', 'onload=', 'onerror='
        ]
        
        for dangerous in dangerous_strings:
            text = text.replace(dangerous, '')
        
        # SQLインジェクション対策（基本的なパターン）
        sql_patterns = [
            r'(\b(union|select|insert|update|delete|drop|create|alter)\b)',
            r'(\b(or|and)\b\s+\d+\s*=\s*\d+)',
            r'(\b(union|select|insert|update|delete|drop|create|alter)\b.*\b(or|and)\b)'
        ]
        
        for pattern in sql_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    def validate_sql_query(self, query: str) -> bool:
        """SQLクエリの検証（基本的なチェック）"""
        dangerous_keywords = [
            'union', 'select', 'insert', 'update', 'delete', 'drop', 
            'create', 'alter', 'exec', 'execute', 'script'
        ]
        
        query_lower = query.lower()
        for keyword in dangerous_keywords:
            if keyword in query_lower:
                return False
        
        return True
    
    def generate_secure_filename(self, original_filename: str) -> str:
        """セキュアなファイル名を生成"""
        # 拡張子を取得
        ext = Path(original_filename).suffix.lower()
        
        # 安全な拡張子のみ許可
        safe_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        if ext not in safe_extensions:
            ext = '.jpg'  # デフォルト
        
        # ランダムなファイル名を生成
        random_name = secrets.token_urlsafe(16)
        return f"{random_name}{ext}"
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]):
        """セキュリティイベントのログ記録"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "details": details
        }
        logger.warning(f"Security event: {log_entry}")

# グローバルセキュリティマネージャーインスタンス
security_manager = SecurityManager() 