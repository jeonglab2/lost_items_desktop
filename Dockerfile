# マルチステージビルド
FROM python:3.9-slim as builder

# 作業ディレクトリを設定
WORKDIR /app

# システム依存関係をインストール
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# 本番用イメージ
FROM python:3.9-slim

# 作業ディレクトリを設定
WORKDIR /app

# システム依存関係をインストール
RUN apt-get update && apt-get install -y \
    libpq5 \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係をコピー
COPY --from=builder /root/.local /root/.local

# 環境変数を設定
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app

# アプリケーションコードをコピー
COPY app/ ./app/
COPY backend/ ./backend/
COPY docs/ ./docs/

# ログディレクトリを作成
RUN mkdir -p logs

# 非rootユーザーを作成
RUN useradd --create-home --shell /bin/bash app
RUN chown -R app:app /app
USER app

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/')" || exit 1

# ポートを公開
EXPOSE 8000

# アプリケーションを起動
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 