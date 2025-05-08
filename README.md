# Docker를 이용한 csp-scrapper-uv 구성
이 가이드는 앞서 구성한 csp-scrapper를 Docker 환경에서 실행하는 방법을 설명합니다. 

# ☁️ Cloud CSP Scrapper
AWS, Azure, GCP의 **주간 업데이트 뉴스레터**를 자동으로 크롤링, 요약, 번역하여 메일로 보내주는 자동화 도구입니다.

## 📄 주요 기능
✅ Azure, AWS, GCP 주간 업데이트 수집  
✅ 영어 요약 → 한국어 번역  
✅ HTML 뉴스레터 이메일 발송  
✅ Docker 기반 배포  
✅ 주간 자동 실행 지원 (Crontab)

**사전 요구 사항:**
* Docker가 서버에 설치되어 있어야 합니다. (docker-install.md 참고)

## 🚀 설치 및 실행
### 1. 클론
```bash
git clone https://github.com/mythe82/csp-scrapper-uv.git
cd csp-scrapper-uv
```

📄 .gitignore
기본적으로 민감 정보와 불필요한 데이터는 Git에 제외됩니다.
```
/app/output/
*.env
*.pyc
__pycache__/
*.log
```

### 2. 환경변수 설정
```bash
cp app/.env.example app/.env
vi app/.env
```

⚙️ .env 환경 변수 예시
```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER=youremail@gmail.com
EMAIL_PASSWORD=yourpassword ex: jaaluqfsrvqkuskc
RECEIVERS=email1@example.com,email2@example.com
```

SMTP, 이메일 수신자 등 정보를 .env에 입력

### 3. Docker 빌드 & 실행
```bash
sudo docker build -t csp-scrapper-uv .
sudo docker run --rm --env-file ./app/.env -v $(pwd)/app/output:/app/output csp-scrapper-uv
```

외부 docker repo에서 받아 바로 실행도 가능
```bash
sudo docker login
sudo docker pull mythe627/csp-scrapper-uv:1
sudo docker run --rm --env-file ./app/.env -v $(pwd)/app/output:/app/output mythe627/csp-scrapper-uv:1
```

### 4. Cron을 이용한 Docker 컨테이너 자동 실행
```bash
crontab -e
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

0 9 * * * cd /home/mythe82/csp-scrapper-uv && /usr/bin/docker run --rm --env-file ./app/.env -v $(pwd)/app/output:/app/output csp-scrapper-uv >> /home/mythe82/csp-cron.log 2>&1
```
