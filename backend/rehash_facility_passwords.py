import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from ..app.database import SessionLocal
from ..app.models import Facility
from ..app.security import security_manager

db = SessionLocal()
for facility in db.query(Facility).all():
    # すでにbcrypt形式ならスキップ
    if facility.password_hash.startswith("$2b$"):
        continue
    # 平文パスワードからハッシュを再生成
    facility.password_hash = security_manager.hash_password(facility.password_hash)
    print(f"Re-hashed: {facility.facility_code}")
db.commit()
db.close()
