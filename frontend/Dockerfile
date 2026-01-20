FROM node:20-alpine

WORKDIR /app

# 패키지 파일 복사
COPY package*.json ./

# 의존성 설치
RUN npm install

# 소스 복사
COPY . .

# 포트 노출
EXPOSE 3000

# 환경 변수 설정 (호스트 바인딩)
ENV HOSTNAME="0.0.0.0"

# 개발 서버 실행 (호스트 바인딩으로 외부 접근 허용)
CMD ["npm", "run", "dev"]
