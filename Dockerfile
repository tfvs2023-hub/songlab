# Advanced Vocal Analysis - Docker Environment
# Ubuntu 기반으로 Essentia + Praat + Torchaudio 환경 구성

FROM ubuntu:22.04

# 기본 패키지 설치 및 환경 설정
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    cmake \
    pkg-config \
    libeigen3-dev \
    libfftw3-dev \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswresample-dev \
    libyaml-dev \
    libtag1-dev \
    libsamplerate0-dev \
    libchromaprint-dev \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Python 심볼릭 링크 생성
RUN ln -s /usr/bin/python3 /usr/bin/python

# 작업 디렉토리 설정
WORKDIR /app

# Python 패키지 먼저 설치
COPY requirements.txt .
RUN pip3 install --no-cache-dir \
    numpy \
    scipy \
    torch \
    torchaudio \
    praat-parselmouth \
    pyloudnorm \
    soundfile \
    fastapi \
    uvicorn[standard] \
    python-multipart \
    aiofiles \
    pydantic

# Essentia 소스에서 빌드 설치
RUN git clone https://github.com/MTG/essentia.git && \
    cd essentia && \
    python3 waf configure --build-static --with-python --with-cpptests --with-examples --with-vamp && \
    python3 waf build && \
    python3 waf install && \
    cd .. && \
    rm -rf essentia

# 라이브러리 경로 설정
ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
ENV PYTHONPATH=/usr/local/lib/python3.10/site-packages:$PYTHONPATH

# 애플리케이션 파일 복사
COPY . .

# 포트 노출
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# 애플리케이션 실행
CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]