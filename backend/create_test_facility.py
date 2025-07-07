import bcrypt
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal, engine
from app.models import Base, Facility
import datetime

def create_test_facility():
    # テーブルを作成
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 既存のテストデータを確認
        existing = db.query(Facility).filter(Facility.facility_code == "FACILITY-01").first()
        if existing:
            print("テスト施設は既に存在します")
            return
        
        # パスワードをハッシュ化
        password = "password"
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # テスト施設を作成
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        test_facility = Facility(
            facility_code="FACILITY-01",
            password_hash=password_hash,
            facility_name="テスト施設",
            created_at=now,
            updated_at=now
        )
        
        db.add(test_facility)
        db.commit()
        print("テスト施設を作成しました")
        print(f"施設コード: FACILITY-01")
        print(f"パスワード: password")
        
    except Exception as e:
        print(f"エラー: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_facility() 