from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Query, Request
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.database import SessionLocal
from app.models import Item, Facility
from app.ai_engine import ai_engine
from app.security import security_manager
from app.logging_config import logging_config
from sqlalchemy import and_
import bcrypt
import math
import tempfile
import os
import time
from fastapi.middleware.cors import CORSMiddleware
import uuid
from fastapi.staticfiles import StaticFiles
from datetime import timezone, timedelta, datetime

app = FastAPI(
    title="拾得物管理システム API",
    description="AI技術を活用した拾得物管理システムのAPI",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://172.23.33.64:3000"],  # React開発サーバーのURL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ミドルウェア: リクエストログ記録
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    # パフォーマンス監視
    if duration > 2.0:  # 2秒を超える場合
        logging_config.log_performance_alert("api_response_time", duration, 2.0)
    
    # APIリクエストログ
    logging_config.log_api_request(
        method=request.method,
        path=str(request.url.path),
        status_code=response.status_code,
        duration=duration
    )
    
    return response

# Pydanticスキーマ
class ItemBase(BaseModel):
    facility_id: int
    found_datetime: str
    accepted_datetime: str
    found_place: str
    category_large: str
    category_medium: str
    name: str
    features: str
    color: str
    status: str = "保管中"
    image_url: str
    finder_type: str
    claims_ownership: bool = False
    claims_reward: bool = False

class ItemCreate(ItemBase):
    pass

class ItemRead(ItemBase):
    item_id: str
    storage_location: str
    created_at: str
    updated_at: str
    class Config:
        orm_mode = True

class RecognizeResponse(BaseModel):
    category_large: str
    category_medium: str
    name: str
    features: str
    color: str
    confidence: float

class TokenRequest(BaseModel):
    facility_code: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", tags=["root"])
def read_root():
    return {"message": "Lost Items API サーバー起動中"}

@app.post("/items", response_model=ItemRead)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    # item_idをUUIDで生成
    item_id = str(uuid.uuid4())

    dt = datetime.fromisoformat(item.accepted_datetime)
    ymd = dt.strftime("%y-%m-%d")
    hour = dt.strftime("%H")
    nn = "01"  # 連番は不要だが、保管場所ロジックのためダミー

    # 保管場所提案ロジック
    if item.claims_ownership:
        storage_location = f"{ymd}-所有権主張"
    elif item.name == "傘":
        storage_location = f"{ymd}-umb"
    elif "食品" in item.features:
        storage_location = f"{ymd}-冷蔵庫"
    else:
        storage_location = f"{ymd}-{nn}"

    JST = timezone(timedelta(hours=9))
    now = datetime.now(JST).isoformat()

    # AIエンジンを使用してベクトル生成
    vector = ai_engine.generate_vector(f"{item.name} {item.features}")
    db_item = Item(
        item_id=item_id,
        storage_location=storage_location,
        vector=vector,  # ベクトルを追加
        created_at=now,
        updated_at=now,
        **item.dict()
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/items", response_model=List[ItemRead])
def list_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Item).order_by(Item.created_at.desc()).offset(skip).limit(limit).all()

@app.get("/items/{item_id}", response_model=ItemRead)
def get_item(item_id: str, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.put("/items/{item_id}", response_model=ItemRead)
def update_item(item_id: str, item: ItemCreate, db: Session = Depends(get_db)):
    db_item = db.query(Item).filter(Item.item_id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    for key, value in item.dict().items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/items/{item_id}")
def delete_item(item_id: str, db: Session = Depends(get_db)):
    db_item = db.query(Item).filter(Item.item_id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(db_item)
    db.commit()
    return {"result": "deleted"}

@app.post("/recognize", response_model=RecognizeResponse)
def recognize_item(file: UploadFile = File(..., description="画像ファイル")):
    # ファイルサイズチェック
    if file.size > security_manager.max_file_size:
        raise HTTPException(status_code=400, detail="ファイルサイズが大きすぎます")
    
    # 一時ファイルに保存
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
        content = file.file.read()
        temp_file.write(content)
        temp_file_path = temp_file.name
    
    try:
        # ファイル検証
        validation_result = security_manager.validate_file_upload(temp_file_path, len(content))
        if not validation_result["valid"]:
            raise HTTPException(status_code=400, detail=validation_result["message"])
        
        # AIエンジンで画像認識（タイムアウト処理付き）
        start_time = time.time()
        try:
            result = ai_engine.recognize_item(temp_file_path)
            duration = time.time() - start_time
            
            # AI操作ログ
            logging_config.log_ai_operation(
                operation="image_recognition",
                duration=duration,
                success=True,
                details={"file_size": len(content), "mime_type": validation_result["mime_type"]}
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logging_config.log_ai_operation(
                operation="image_recognition",
                duration=duration,
                success=False,
                details={"error": str(e)}
            )
            raise HTTPException(status_code=500, detail="画像認識に失敗しました")
        
        return RecognizeResponse(
            category_large=result["category_large"],
            category_medium=result["category_medium"],
            name=result["name"],
            features=result["features"],
            color=result["color"],
            confidence=result["confidence"]
        )
    finally:
        # 一時ファイルを削除
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

@app.post("/auth/token", response_model=TokenResponse)
def auth_token(request: TokenRequest, db: Session = Depends(get_db)):
    # 入力サニタイズ
    facility_code = security_manager.sanitize_input(request.facility_code)
    password = request.password
    
    facility = db.query(Facility).filter(Facility.facility_code == facility_code).first()
    if not facility or not security_manager.verify_password(password, facility.password_hash):
        # セキュリティイベントログ
        logging_config.log_security_event(
            "auth_failure",
            {"facility_code": facility_code, "reason": "invalid_credentials"},
            user_id=facility_code
        )
        raise HTTPException(status_code=401, detail="認証失敗")
    
    # アクセストークンとリフレッシュトークンを生成
    token_data = {
        "facility_id": facility.id,
        "facility_code": facility.facility_code,
        "user_type": "facility"
    }
    
    access_token = security_manager.create_access_token(token_data)
    refresh_token = security_manager.create_refresh_token(token_data)
    
    # 認証成功ログ
    logging_config.log_security_event(
        "auth_success",
        {"facility_code": facility_code},
        user_id=facility_code
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )

def calculate_similarity(vec1: List[float], vec2: List[float]) -> float:
    # AIエンジンを使用して類似度計算
    return ai_engine.calculate_similarity(vec1, vec2)

@app.get("/items/search", response_model=List[ItemRead])
def search_items(
    keywords: str = Query(None, description="品名・特徴のANDキーワード（スペース区切り）"),
    found_place: str = Query(None, description="拾得場所"),
    date_from: str = Query(None, description="拾得日(開始)"),
    date_to: str = Query(None, description="拾得日(終了)"),
    semantic_search: bool = Query(False, description="セマンティック検索有効化"),
    db: Session = Depends(get_db)
):
    query = db.query(Item)
    # ANDキーワード検索
    if keywords:
        for kw in keywords.split():
            query = query.filter(
                (Item.name.contains(kw)) | (Item.features.contains(kw))
            )
    if found_place:
        query = query.filter(Item.found_place.contains(found_place))
    if date_from:
        query = query.filter(Item.found_datetime >= date_from)
    if date_to:
        query = query.filter(Item.found_datetime <= date_to)
    
    items = query.all()
    
    # セマンティック検索が有効な場合、ベクトル類似度でランキング
    if semantic_search and keywords:
        # クエリをベクトル化
        query_vector = ai_engine.generate_vector(keywords)
        # 類似度を計算してランキング
        items_with_similarity = []
        for item in items:
            if item.vector:
                similarity = calculate_similarity(query_vector, item.vector)
                items_with_similarity.append((item, similarity))
            else:
                items_with_similarity.append((item, 0.0))
        # 類似度で降順ソート
        items_with_similarity.sort(key=lambda x: x[1], reverse=True)
        return [item for item, _ in items_with_similarity]
    
    return items

@app.post("/items/{item_id}/image")
def upload_item_image(item_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    # 画像ファイルを保存（例: static/images/ ディレクトリに保存）
    import os
    from uuid import uuid4

    # 保存先ディレクトリ
    save_dir = "static/images"
    os.makedirs(save_dir, exist_ok=True)
    # 一意なファイル名を生成
    ext = os.path.splitext(file.filename)[1]
    filename = f"{item_id}_{uuid4().hex}{ext}"
    file_path = os.path.join(save_dir, filename)

    with open(file_path, "wb") as f:
        f.write(file.file.read())

    # 画像URLをDBに保存（例: /static/images/filename）
    image_url = f"/static/images/{filename}"
    item = db.query(Item).filter(Item.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.image_url = image_url
    db.commit()
    db.refresh(item)
    return {"image_url": image_url}

app.mount("/static", StaticFiles(directory="static"), name="static")