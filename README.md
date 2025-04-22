# Docker를 이용한 csp-scrapper-uv 구성
이 가이드는 앞서 구성한 csp-scrapper를 Docker 환경에서 실행하는 방법을 설명합니다. 

**사전 요구 사항:**
* Docker가 서버에 설치되어 있어야 합니다. (docker-install.md 참고)
* 프로젝트 디렉토리에 `main.py`, `banner.png`, `requirements.txt` 파일이 준비되어 있어야 합니다. (`.env` 파일은 이미지에 직접 복사하지 않고 실행 시 환경 변수로 주입합니다.)

---

## 1. Dockerfile 작성

프로젝트 루트 디렉토리( `scraper.py` 등이 있는 곳)에 `Dockerfile`이라는 이름의 파일을 생성하고 아래 내용을 작성합니다.

```dockerfile
# Dockerfile

# 1. 베이스 이미지 선택 (Python 3.11 슬림 버전 사용)
FROM python:3.11-slim

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 시스템 환경 설정 및 필수 패키지 설치
#    - FONTS_NANUM: 한글 폰트 설치 (matplotlib 차트용)
#    - CURL: uv 설치용
#    - build-essential: 일부 파이썬 패키지 빌드에 필요할 수 있음 (uv가 휠을 잘 처리하면 불필요할 수도 있음)
#    - 불필요한 apt 캐시 삭제하여 이미지 크기 줄이기
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        fonts-nanum* \
        curl \
        build-essential \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 4. uv 설치
RUN curl -LsSf [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh
ENV PATH="/root/.local/bin:${PATH}"

# 5. 애플리케이션 파일 복사
#    - requirements.txt 를 먼저 복사하여 의존성 캐싱 활용
COPY requirements.txt .
COPY scraper.py .
COPY banner.png .

# 6. Python 의존성 설치 (uv 사용, --no-cache 로 이미지 크기 최적화)
RUN uv pip install --no-cache-dir -r requirements.txt

# 7. Playwright 브라우저 설치 (uv run 사용)
RUN uv run playwright install chromium

# 8. Matplotlib 폰트 캐시 재생성 (설치된 한글 폰트 인식)
RUN uv run python -c "import matplotlib.font_manager; matplotlib.font_manager._load_fontmanager(try_read_cache=False)"

# 9. 컨테이너 실행 시 실행될 명령어 설정
#    - 환경 변수는 docker run 시점에 주입
CMD ["uv", "run", "python", "scraper.py"]

Dockerfile 설명:
 * FROM python:3.11-slim: 파이썬 3.11 슬림 버전을 기반으로 이미지를 만듭니다.
 * WORKDIR /app: 컨테이너 내 작업 디렉토리를 /app으로 설정합니다. 이후 명령어는 이 디렉토리 기준으로 실행됩니다.
 * RUN apt-get ...: 데비안/우분투 패키지 관리자인 apt-get을 이용해 나눔 폰트, curl 등을 설치합니다. --no-install-recommends와 apt-get clean 등으로 이미지 크기를 최적화합니다.
 * RUN curl ... | sh: uv 설치 스크립트를 실행합니다.
 * ENV PATH=...: 설치된 uv를 시스템 경로에 추가합니다.
 * COPY ... .: 로컬 프로젝트 파일들을 컨테이너의 /app 디렉토리로 복사합니다.
 * RUN uv pip install ...: uv를 이용해 requirements.txt에 명시된 파이썬 패키지들을 설치합니다. --no-cache-dir 옵션으로 불필요한 캐시를 남기지 않아 이미지 크기를 줄입니다.
 * RUN uv run playwright install chromium: 컨테이너 내 환경에서 Playwright의 크로미움 브라우저를 설치합니다.
 * RUN uv run python -c "...": 컨테이너 빌드 시점에 matplotlib 폰트 캐시를 갱신하여 나눔 폰트를 인식하도록 합니다.
 * CMD ["uv", "run", "python", "scraper.py"]: 컨테이너가 시작될 때 기본으로 실행될 명령어를 지정합니다.
2. Docker 이미지 빌드
Dockerfile이 있는 디렉토리에서 아래 명령어를 실행하여 Docker 이미지를 빌드합니다. -t 옵션으로 이미지 이름과 태그를 지정합니다 (예: cloud-scraper:latest).
docker build -t cloud-scraper:latest .

빌드가 완료되면 docker images 명령어로 생성된 이미지를 확인할 수 있습니다.
3. Docker 컨테이너 실행
빌드된 이미지를 사용하여 컨테이너를 실행합니다. 이때, .env 파일에 있던 환경 변수들을 docker run 명령어의 -e 옵션을 통해 주입해야 합니다. 또한, 스크립트가 생성하는 JSON 파일을 호스트 머신에 저장하기 위해 볼륨 마운트(-v)를 사용합니다.
# docker run 명령어 (한 줄로 실행하거나 '\' 사용하여 여러 줄로 작성)
docker run --rm \
  -e SMTP_SERVER="smtp.example.com" \
  -e SMTP_PORT="587" \
  -e SENDER="your_email@example.com" \
  -e EMAIL_PASSWORD="your_very_secret_email_password_or_app_password" \
  -e RECEIVERS="recipient1@example.com,recipient2@example.com" \
  -v "$(pwd)/output:/app/output" \
  cloud-scraper:latest

docker run 옵션 설명:
 * --rm: 컨테이너 실행이 완료되면 자동으로 컨테이너를 삭제합니다. 일회성 작업에 유용합니다.
 * -e VARIABLE_NAME="value": 컨테이너 내부에 환경 변수를 설정합니다. .env 파일에 있던 각 변수를 -e 옵션으로 전달해야 합니다. 보안에 유의하세요. (비밀번호 등 민감 정보)
 * -v "$(pwd)/output:/app/output": 호스트 머신의 현재 디렉토리 아래 output 폴더와 컨테이너 내부의 /app/output 폴더를 연결(마운트)합니다. 이렇게 하면 스크립트가 컨테이너 내 /app/output에 저장하는 JSON 파일이 호스트의 output 폴더에 실제로 저장되어 컨테이너가 사라져도 결과가 유지됩니다.
 * cloud-scraper:latest: 실행할 Docker 이미지의 이름과 태그입니다.
중요: 위 명령어의 환경 변수 값들(smtp.example.com, your_email@example.com 등)은 실제 값으로 반드시 변경해야 합니다.
4. Cron을 이용한 Docker 컨테이너 자동 실행
호스트 서버의 cron을 사용하여 주기적으로 docker run 명령어를 실행하도록 설정할 수 있습니다.
crontab -e 명령으로 crontab 편집기를 열고 아래와 같이 등록합니다. (예: 매주 월요일 오전 7시에 실행)
# 예시: 매주 월요일 오전 7시에 Docker 컨테이너 실행
# 실제 환경 변수 값으로 변경해야 합니다.
# $(pwd) 대신 output 디렉토리의 절대 경로를 사용하는 것이 더 안정적일 수 있습니다.

0 7 * * 1 /usr/bin/docker run --rm -e SMTP_SERVER="smtp.example.com" -e SMTP_PORT="587" -e SENDER="your_email@example.com" -e EMAIL_PASSWORD="your_secret_password" -e RECEIVERS="recipient1@example.com,recipient2@example.com" -v /path/to/your/project/output:/app/output cloud-scraper:latest >> /path/to/your/project/cron_docker.log 2>&1

Cron 항목 설명:
 * 0 7 * * 1: 실행 주기 (매주 월요일 오전 7시)
 * /usr/bin/docker run ...: docker run 명령어를 사용하여 컨테이너를 실행합니다. docker 명령어의 절대 경로를 사용하는 것이 좋습니다 (which docker로 확인).
 * -e ...: 환경 변수를 직접 명시합니다.
 * -v /path/to/your/project/output:/app/output: 호스트의 output 디렉토리 절대 경로와 컨테이너의 /app/output을 연결합니다. $(pwd) 대신 절대 경로를 사용하는 것이 cron 환경에서 더 안전합니다.
 * cloud-scraper:latest: 실행할 이미지 이름
 * >> /path/to/your/project/cron_docker.log 2>&1: docker run 명령어의 실행 결과 및 오류를 로그 파일에 저장합니다.
5. 장점 및 고려사항
 * 환경 일관성: Docker를 사용하면 개발, 테스트, 운영 환경 모두 동일한 환경에서 스크립트를 실행할 수 있습니다.
 * 쉬운 배포: Docker 이미지만 있으면 어디든 쉽게 배포할 수 있습니다.
 * 의존성 격리: 호스트 시스템에 파이썬 버전이나 라이브러리, 폰트 등을 직접 설치할 필요가 없습니다.
 * 환경 변수 관리: -e 옵션으로 환경 변수를 주입하는 방식은 .env 파일을 직접 관리하는 것보다 유연하지만, 명령어에 민감 정보가 노출될 수 있습니다. 더 안전한 방법으로 Docker Secrets나 다른 설정 관리 도구를 사용하는 것을 고려할 수 있습니다. (고급)
 * 이미지 크기: Dockerfile 최적화(멀티 스테이지 빌드 등)를 통해 이미지 크기를 더 줄일 수 있습니다.
이제 Docker를 사용하여 클라우드 업데이트 스크래퍼를 컨테이너 환경에서 실행하고, cron으로 자동화할 수 있습니다.
