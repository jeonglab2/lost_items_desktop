import logging
import logging.handlers
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json
import time
from pathlib import Path

class AuditLogger:
    """監査ログ専用のロガー"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # 監査ログファイルの設定
        audit_log_file = self.log_dir / "audit.log"
        
        # 監査ログフォーマッター
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(user_id)s | %(action)s | %(resource)s | %(details)s'
        )
        
        # ファイルハンドラー（日次ローテーション）
        file_handler = logging.handlers.TimedRotatingFileHandler(
            audit_log_file,
            when='midnight',
            interval=1,
            backupCount=365,  # 1年間保持
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        
        # ロガーの設定
        self.logger = logging.getLogger('audit')
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)
        self.logger.propagate = False
    
    def log_event(self, user_id: str, action: str, resource: str, details: Dict[str, Any]):
        """監査イベントを記録"""
        extra = {
            'user_id': user_id,
            'action': action,
            'resource': resource,
            'details': json.dumps(details, ensure_ascii=False)
        }
        self.logger.info('Audit event', extra=extra)

class PerformanceMonitor:
    """パフォーマンス監視"""
    
    def __init__(self):
        self.metrics = {}
    
    def start_timer(self, operation: str):
        """タイマー開始"""
        self.metrics[operation] = {
            'start_time': time.time(),
            'end_time': None,
            'duration': None
        }
    
    def end_timer(self, operation: str) -> float:
        """タイマー終了"""
        if operation in self.metrics:
            self.metrics[operation]['end_time'] = time.time()
            self.metrics[operation]['duration'] = (
                self.metrics[operation]['end_time'] - 
                self.metrics[operation]['start_time']
            )
            return self.metrics[operation]['duration']
        return 0.0
    
    def get_metrics(self) -> Dict[str, Any]:
        """メトリクスを取得"""
        return self.metrics.copy()

class LoggingConfig:
    """ログ設定管理"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # アプリケーションログの設定
        self._setup_application_logger()
        
        # 監査ログの設定
        self.audit_logger = AuditLogger(log_dir)
        
        # パフォーマンス監視
        self.performance_monitor = PerformanceMonitor()
    
    def _setup_application_logger(self):
        """アプリケーションログの設定"""
        # アプリケーションログファイル
        app_log_file = self.log_dir / "application.log"
        
        # フォーマッター
        formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
        )
        
        # ファイルハンドラー（日次ローテーション、30日間保持）
        file_handler = logging.handlers.TimedRotatingFileHandler(
            app_log_file,
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        
        # コンソールハンドラー
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # ルートロガーの設定
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
    
    def log_api_request(self, method: str, path: str, status_code: int, 
                       duration: float, user_id: Optional[str] = None):
        """APIリクエストをログ記録"""
        logger = logging.getLogger('api')
        
        log_data = {
            'method': method,
            'path': path,
            'status_code': status_code,
            'duration': f"{duration:.3f}s",
            'user_id': user_id or 'anonymous'
        }
        
        if status_code >= 400:
            logger.warning(f"API request: {log_data}")
        else:
            logger.info(f"API request: {log_data}")
    
    def log_security_event(self, event_type: str, details: Dict[str, Any], 
                          user_id: Optional[str] = None):
        """セキュリティイベントをログ記録"""
        logger = logging.getLogger('security')
        
        log_data = {
            'event_type': event_type,
            'details': details,
            'user_id': user_id or 'anonymous'
        }
        
        logger.warning(f"Security event: {log_data}")
        
        # 監査ログにも記録
        self.audit_logger.log_event(
            user_id=user_id or 'anonymous',
            action=event_type,
            resource='security',
            details=details
        )
    
    def log_ai_operation(self, operation: str, duration: float, 
                        success: bool, details: Dict[str, Any]):
        """AI操作をログ記録"""
        logger = logging.getLogger('ai')
        
        log_data = {
            'operation': operation,
            'duration': f"{duration:.3f}s",
            'success': success,
            'details': details
        }
        
        if success:
            logger.info(f"AI operation: {log_data}")
        else:
            logger.error(f"AI operation failed: {log_data}")
    
    def log_database_operation(self, operation: str, table: str, 
                              duration: float, success: bool):
        """データベース操作をログ記録"""
        logger = logging.getLogger('database')
        
        log_data = {
            'operation': operation,
            'table': table,
            'duration': f"{duration:.3f}s",
            'success': success
        }
        
        if success:
            logger.info(f"Database operation: {log_data}")
        else:
            logger.error(f"Database operation failed: {log_data}")
    
    def log_performance_alert(self, metric: str, value: float, threshold: float):
        """パフォーマンスアラートをログ記録"""
        logger = logging.getLogger('performance')
        
        log_data = {
            'metric': metric,
            'value': value,
            'threshold': threshold,
            'exceeded': value > threshold
        }
        
        logger.warning(f"Performance alert: {log_data}")

# グローバルログ設定インスタンス
logging_config = LoggingConfig() 