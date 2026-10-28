FROM python:3.13.5-slim-bookworm AS build-image

# Install system dependencies needed for downloading, extracting and building
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends wget xz-utils unzip git cmake build-essential python3 && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

RUN wget -q https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz

RUN mkdir -p ffmpeg-tmp && \
    tar -xf ffmpeg-release-amd64-static.tar.xz --strip-components 1 -C ffmpeg-tmp && \
    cp -v ffmpeg-tmp/ffmpeg ffmpeg-tmp/ffprobe ffmpeg-tmp/qt-faststart /usr/local/bin && \
    rm -rf ffmpeg-tmp ffmpeg-release-amd64-static.tar.xz

# Build Bento4 from source so the binaries match the container architecture
# (the prebuilt x86_64 binaries are dynamically linked and cannot run on arm64).
RUN wget -q --tries=5 --waitretry=10 --timeout=60 -O /tmp/bento4.zip https://codeload.github.com/axiomatic-systems/Bento4/zip/refs/tags/v1.6.0-637 && \
    unzip -q /tmp/bento4.zip -d /tmp && \
    mv /tmp/Bento4-1.6.0-637 /tmp/bento4-src && \
    cmake -S /tmp/bento4-src -B /tmp/bento4-src/cmakebuild -DCMAKE_BUILD_TYPE=Release && \
    cmake --build /tmp/bento4-src/cmakebuild -j"$(nproc)" && \
    mkdir -p /home/mediacms.io/bento4/bin /home/mediacms.io/bento4/utils && \
    find /tmp/bento4-src/cmakebuild -maxdepth 1 -type f -executable -exec cp {} /home/mediacms.io/bento4/bin/ \; && \
    cp /tmp/bento4-src/Source/Python/wrappers/mp4hls /tmp/bento4-src/Source/Python/wrappers/mp4dash /tmp/bento4-src/Source/Python/wrappers/mp4dashclone /home/mediacms.io/bento4/bin/ && \
    cp -r /tmp/bento4-src/Source/Python/utils/* /home/mediacms.io/bento4/utils/ && \
    rm -rf /tmp/bento4-src /tmp/bento4.zip

############ BASE RUNTIME IMAGE ############
FROM python:3.13.5-slim-bookworm AS base

SHELL ["/bin/bash", "-c"]

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV CELERY_APP='cms'
ENV VIRTUAL_ENV=/home/mediacms.io
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install system dependencies first
RUN apt-get update -y && \
    apt-get -y upgrade && \
    apt-get install --no-install-recommends -y \
        supervisor \
        nginx \
        imagemagick \
        procps \
        build-essential \
        pkg-config \
        zlib1g-dev \
        zlib1g \
        libxml2-dev \
        libxmlsec1-dev \
        libxmlsec1-openssl \
        libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up virtualenv first
RUN mkdir -p /home/mediacms.io/mediacms/{logs} && \
    cd /home/mediacms.io && \
    python3 -m venv $VIRTUAL_ENV

# Copy requirements files
COPY requirements.txt requirements-dev.txt ./

# Install Python dependencies using pip (within virtualenv)
ARG DEVELOPMENT_MODE=False
RUN pip install --no-cache-dir uv && \
    uv pip install --no-binary lxml --no-binary xmlsec -r requirements.txt && \
    if [ "$DEVELOPMENT_MODE" = "True" ]; then \
        echo "Installing development dependencies..." && \
        uv pip install -r requirements-dev.txt; \
    fi && \
    apt-get purge -y --auto-remove \
        build-essential \
        pkg-config \
        libxml2-dev \
        libxmlsec1-dev \
        libpq-dev

# Copy ffmpeg and Bento4 from build image
COPY --from=build-image /usr/local/bin/ffmpeg /usr/local/bin/ffmpeg
COPY --from=build-image /usr/local/bin/ffprobe /usr/local/bin/ffprobe
COPY --from=build-image /usr/local/bin/qt-faststart /usr/local/bin/qt-faststart
COPY --from=build-image /home/mediacms.io/bento4 /home/mediacms.io/bento4

# Copy application files
COPY . /home/mediacms.io/mediacms
WORKDIR /home/mediacms.io/mediacms

# required for sprite thumbnail generation for large video files
COPY deploy/docker/policy.xml /etc/ImageMagick-6/policy.xml

# Set process control environment variables
ENV ENABLE_UWSGI='yes' \
    ENABLE_NGINX='yes' \
    ENABLE_CELERY_BEAT='yes' \
    ENABLE_CELERY_SHORT='yes' \
    ENABLE_CELERY_LONG='yes' \
    ENABLE_MIGRATIONS='yes'

EXPOSE 9000 80

RUN chmod +x ./deploy/docker/entrypoint.sh

ENTRYPOINT ["./deploy/docker/entrypoint.sh"]
CMD ["./deploy/docker/start.sh"]

############ FULL IMAGE ############
FROM base AS full
COPY requirements-full.txt ./
RUN mkdir -p /root/.cache/ && \
    chmod go+rwx /root/ && \
    chmod go+rwx /root/.cache/
RUN uv pip install -r requirements-full.txt