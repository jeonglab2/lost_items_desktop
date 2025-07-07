import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db, Base
from app.models import Item, Facility
from app.security import security_manager
from app.ai_engine import ai_engine
import tempfile
import os
from PIL import Image
import numpy as np

# テスト用データベース
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def setup_database():
    """テスト用データベースのセットアップ"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    """テストクライアント"""
    return TestClient(app)

@pytest.fixture
def sample_facility():
    """サンプル施設データ"""
    return {
        "facility_code": "TEST001",
        "name": "テスト施設",
        "password_hash": security_manager.hash_password("testpass123")
    }

@pytest.fixture
def sample_item():
    """サンプルアイテムデータ"""
    return {
        "facility_id": 1,
        "found_datetime": "2024-01-15T10:30:00",
        "accepted_datetime": "2024-01-15T10:35:00",
        "found_place": "1階ロビー",
        "category_large": "かばん類",
        "category_medium": "手提げかばん",
        "name": "ハンドバッグ",
        "features": "黒色、革製、ブランドロゴあり",
        "color": "黒",
        "status": "保管中",
        "image_url": "test_image.jpg",
        "finder_type": "一般",
        "claims_ownership": False,
        "claims_reward": False
    }

@pytest.fixture
def sample_image():
    """テスト用画像ファイル"""
    # テスト用の画像を作成
    img = Image.new('RGB', (100, 100), color='red')
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
        img.save(tmp_file.name, 'JPEG')
        yield tmp_file.name
    os.unlink(tmp_file.name)

class TestAuthentication:
    """認証機能のテスト"""
    
    def test_auth_token_success(self, client, setup_database, sample_facility):
        """認証トークン取得成功テスト"""
        # 施設をデータベースに追加
        db = TestingSessionLocal()
        facility = Facility(**sample_facility)
        db.add(facility)
        db.commit()
        db.close()
        
        response = client.post("/auth/token", json={
            "facility_code": "TEST001",
            "password": "testpass123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_auth_token_invalid_credentials(self, client, setup_database):
        """無効な認証情報テスト"""
        response = client.post("/auth/token", json={
            "facility_code": "INVALID",
            "password": "wrongpass"
        })
        
        assert response.status_code == 401
    
    def test_auth_token_missing_fields(self, client):
        """必須フィールド不足テスト"""
        response = client.post("/auth/token", json={
            "facility_code": "TEST001"
        })
        
        assert response.status_code == 422

class TestItemRegistration:
    """アイテム登録機能のテスト"""
    
    def test_create_item_success(self, client, setup_database, sample_item):
        """アイテム登録成功テスト"""
        response = client.post("/items", json=sample_item)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == sample_item["name"]
        assert data["item_id"] is not None
        assert data["storage_location"] is not None
    
    def test_create_item_missing_required_fields(self, client, setup_database):
        """必須フィールド不足テスト"""
        incomplete_item = {
            "facility_id": 1,
            "name": "テストアイテム"
        }
        
        response = client.post("/items", json=incomplete_item)
        assert response.status_code == 422
    
    def test_create_item_with_ownership_claim(self, client, setup_database, sample_item):
        """所有権主張ありのアイテム登録テスト"""
        sample_item["claims_ownership"] = True
        
        response = client.post("/items", json=sample_item)
        
        assert response.status_code == 200
        data = response.json()
        assert "所有権主張" in data["storage_location"]
    
    def test_create_item_umbrella(self, client, setup_database, sample_item):
        """傘のアイテム登録テスト"""
        sample_item["name"] = "傘"
        
        response = client.post("/items", json=sample_item)
        
        assert response.status_code == 200
        data = response.json()
        assert "umb" in data["storage_location"]

class TestItemSearch:
    """アイテム検索機能のテスト"""
    
    def test_search_items_keywords(self, client, setup_database, sample_item):
        """キーワード検索テスト"""
        # アイテムを登録
        client.post("/items", json=sample_item)
        
        response = client.get("/items/search?keywords=ハンドバッグ")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert data[0]["name"] == "ハンドバッグ"
    
    def test_search_items_semantic(self, client, setup_database, sample_item):
        """セマンティック検索テスト"""
        # アイテムを登録
        client.post("/items", json=sample_item)
        
        response = client.get("/items/search?keywords=バッグ&semantic_search=true")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
    
    def test_search_items_date_range(self, client, setup_database, sample_item):
        """日付範囲検索テスト"""
        # アイテムを登録
        client.post("/items", json=sample_item)
        
        response = client.get("/items/search?date_from=2024-01-01&date_to=2024-12-31")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

class TestAIEngine:
    """AIエンジンのテスト"""
    
    def test_recognize_item(self, sample_image):
        """画像認識テスト"""
        result = ai_engine.recognize_item(sample_image)
        
        assert "category_large" in result
        assert "category_medium" in result
        assert "name" in result
        assert "features" in result
        assert "color" in result
        assert "confidence" in result
        assert 0.0 <= result["confidence"] <= 1.0
    
    def test_generate_vector(self):
        """ベクトル生成テスト"""
        text = "ハンドバッグ 黒色 革製"
        vector = ai_engine.generate_vector(text)
        
        assert isinstance(vector, list)
        assert len(vector) > 0
        assert all(isinstance(x, float) for x in vector)
    
    def test_calculate_similarity(self):
        """類似度計算テスト"""
        vec1 = [0.1, 0.2, 0.3]
        vec2 = [0.1, 0.2, 0.3]
        
        similarity = ai_engine.calculate_similarity(vec1, vec2)
        
        assert isinstance(similarity, float)
        assert 0.0 <= similarity <= 1.0

class TestSecurity:
    """セキュリティ機能のテスト"""
    
    def test_password_hashing(self):
        """パスワードハッシュ化テスト"""
        password = "testpassword123"
        hashed = security_manager.hash_password(password)
        
        assert hashed != password
        assert security_manager.verify_password(password, hashed)
        assert not security_manager.verify_password("wrongpassword", hashed)
    
    def test_token_creation_and_verification(self):
        """トークン生成・検証テスト"""
        data = {"user_id": "test_user", "facility_id": 1}
        
        access_token = security_manager.create_access_token(data)
        refresh_token = security_manager.create_refresh_token(data)
        
        # トークン検証
        access_payload = security_manager.verify_token(access_token)
        refresh_payload = security_manager.verify_token(refresh_token)
        
        assert access_payload is not None
        assert refresh_payload is not None
        assert access_payload["user_id"] == "test_user"
        assert refresh_payload["type"] == "refresh"
    
    def test_input_sanitization(self):
        """入力サニタイズテスト"""
        dangerous_input = "<script>alert('xss')</script>"
        sanitized = security_manager.sanitize_input(dangerous_input)
        
        assert "<script>" not in sanitized
        assert "alert" not in sanitized
    
    def test_file_validation(self, sample_image):
        """ファイル検証テスト"""
        file_size = os.path.getsize(sample_image)
        result = security_manager.validate_file_upload(sample_image, file_size)
        
        assert result["valid"] is True
        assert result["mime_type"] is not None

class TestPerformance:
    """パフォーマンステスト"""
    
    def test_search_response_time(self, client, setup_database, sample_item):
        """検索応答時間テスト"""
        # 複数のアイテムを登録
        for i in range(10):
            item = sample_item.copy()
            item["name"] = f"テストアイテム{i}"
            client.post("/items", json=item)
        
        import time
        start_time = time.time()
        response = client.get("/items/search?keywords=テスト")
        end_time = time.time()
        
        duration = end_time - start_time
        
        assert response.status_code == 200
        assert duration < 2.0  # 2秒以内
    
    def test_ai_recognition_response_time(self, sample_image):
        """AI認識応答時間テスト"""
        import time
        start_time = time.time()
        result = ai_engine.recognize_item(sample_image)
        end_time = time.time()
        
        duration = end_time - start_time
        
        assert result is not None
        assert duration < 10.0  # 10秒以内（AI処理の制限）

class TestErrorHandling:
    """エラーハンドリングテスト"""
    
    def test_invalid_item_id(self, client, setup_database):
        """無効なアイテムIDテスト"""
        response = client.get("/items/INVALID-ID")
        assert response.status_code == 404
    
    def test_invalid_file_upload(self, client):
        """無効なファイルアップロードテスト"""
        # 空のファイル
        files = {"file": ("test.txt", b"", "text/plain")}
        response = client.post("/recognize", files=files)
        
        # エラーが適切に処理されることを確認
        assert response.status_code in [400, 422, 500]
    
    def test_database_connection_error(self, client):
        """データベース接続エラーテスト"""
        # データベース接続を無効化してテスト
        # 実際の実装では、データベース接続エラーを適切にハンドリングする必要がある
        pass

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 