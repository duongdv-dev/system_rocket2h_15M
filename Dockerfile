# ==============================================================================
# DOCKERFILE ĐÓNG GÓI HOÀN CHỈNH (PRODUCTION STANDALONE IMAGE)
# ==============================================================================

# STAGE 1: Build React Frontend
FROM node:20-slim AS frontend-builder
WORKDIR /build
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# STAGE 2: Python Web Server & Quant Engine
FROM python:3.11-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Copy mã nguồn backend & engine
COPY data/ ./data/
COPY engine/ ./engine/
COPY server/ ./server/

# Copy bản build frontend vào đúng vị trí để server/app.py phục vụ
COPY --from=frontend-builder /build/dist ./frontend/dist

EXPOSE 8080

CMD ["python3", "server/app.py", "--host", "0.0.0.0", "--port", "8080"]
