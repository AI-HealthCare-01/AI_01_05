FROM node:20-alpine AS build

WORKDIR /app

# 1. 의존성 설치 (캐시 최적화: package*.json 먼저 복사)
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# 2. 소스 복사 및 빌드
COPY frontend/ ./
RUN npm run build

# 빌드 결과물: /app/dist
