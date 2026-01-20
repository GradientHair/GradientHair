FROM python:3.12-slim

WORKDIR /app

# uv 설치
RUN pip install uv

# 프로젝트 파일 복사
COPY pyproject.toml uv.lock ./

# 의존성 설치
RUN uv sync

# 소스 복사
COPY . .

# 포트 노출
EXPOSE 8000

# 개발 서버 실행 (핫 리로드 활성화)
CMD ["uv", "run", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
