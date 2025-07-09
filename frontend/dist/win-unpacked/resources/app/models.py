from sqlalchemy import Column, String, Integer, Boolean, Date, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import ARRAY

Base = declarative_base()

class Item(Base):
    __tablename__ = "items"

    item_id = Column(String(255), primary_key=True, comment="拾得物ID。yy-mm-dd-h-nn形式")
    facility_id = Column(Integer, nullable=False, comment="登録施設ID")
    category_large = Column(String(100), comment="分類(大)")
    category_medium = Column(String(100), comment="分類(中)")
    claims_ownership = Column(Boolean, nullable=False, default=False, comment="所有権主張")
    claims_reward = Column(Boolean, nullable=False, default=False, comment="報労金請求")
    found_datetime = Column(String, nullable=False, comment="拾得日時（TIMESTAMP WITH TIME ZONE）")
    accepted_datetime = Column(String, nullable=False, comment="受付日時（TIMESTAMP WITH TIME ZONE）")
    found_place = Column(String(255), nullable=False, comment="拾得場所")
    name = Column(String(255), nullable=False, comment="品名")
    features = Column(String, nullable=False, comment="特徴")
    color = Column(String(50), nullable=False, comment="色")
    status = Column(String(50), nullable=False, default="保管中", comment="状態（保管中、返還済、警察届出済、廃棄済）")
    storage_location = Column(String(255), nullable=False, comment="保管場所")
    image_url = Column(String(255), nullable=False, comment="画像ファイルのURL")
    finder_type = Column(String(50), nullable=False, comment="拾得者の属性（第三者、施設占有者）")
    created_at = Column(String, nullable=False, comment="作成日時（TIMESTAMP WITH TIME ZONE）")
    updated_at = Column(String, nullable=False, comment="更新日時（TIMESTAMP WITH TIME ZONE）")
    vector = Column(ARRAY(Float), nullable=True, comment="品名・特徴の埋め込みベクトル（セマンティック検索用）")
    # TODO: TIMESTAMP型は実際のDB接続時にDateTime型へ修正
    # TODO: 必要に応じて全文検索用のベクトルカラムやインデックスも追加

class Facility(Base):
    __tablename__ = "facilities"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="施設ID")
    facility_code = Column(String(255), unique=True, nullable=False, comment="施設コード")
    password_hash = Column(String(255), nullable=False, comment="ハッシュ化パスワード")
    facility_name = Column(String(255), nullable=False, comment="施設名")
    created_at = Column(String, nullable=False, comment="作成日時")
    updated_at = Column(String, nullable=False, comment="更新日時")
