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
COPY main.py .
COPY banner.png .

# 6. Python 의존성 설치 (uv 사용, --no-cache 로 이미지 크기 최적화)
RUN uv pip install --no-cache-dir -r requirements.txt

# 7. Playwright 브라우저 설치 (uv run 사용)
RUN uv run playwright install chromium

# 8. Matplotlib 폰트 캐시 재생성 (설치된 한글 폰트 인식)
RUN uv run python -c "import matplotlib.font_manager; matplotlib.font_manager._load_fontmanager(try_read_cache=False)"

# 9. 컨테이너 실행 시 실행될 명령어 설정
#    - 환경 변수는 docker run 시점에 주입
CMD ["uv", "run", "python", "main.py"]
