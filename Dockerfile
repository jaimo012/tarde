# 클라우드타입 배포용 Dockerfile
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# pip 업그레이드
RUN pip install --upgrade pip

# 클라우드타입용 requirements 복사 및 설치
COPY requirements-cloudtype.txt .
RUN pip install --no-cache-dir -r requirements-cloudtype.txt

# 소스 코드 복사
COPY . .

# 로그 디렉토리 생성
RUN mkdir -p /tmp/logs

# 환경변수 설정
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 포트 설정
EXPOSE 8080

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# 실행 명령어
CMD ["python", "cloudtype_run.py"]
