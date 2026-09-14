# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS frontend-build
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
ARG PLATFORM_TOOLS_VERSION=35.0.2
ARG SCRCPY_VERSION=4.1
ARG SCRCPY_SHA256=ad56ae8bfeedf41e824945c11dbf55fcb092b3e615b9b486f48a50e30d389635
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/opt/android-platform-tools:${PATH}" ADB_PATH=/opt/android-platform-tools/adb
WORKDIR /app
RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates curl novnc unzip websockify x11vnc xvfb \
    && curl --fail --location --retry 3 "https://dl.google.com/android/repository/platform-tools_r${PLATFORM_TOOLS_VERSION}-linux.zip" --output /tmp/platform-tools.zip \
    && unzip -q /tmp/platform-tools.zip -d /opt \
    && mv /opt/platform-tools /opt/android-platform-tools \
    && curl --fail --location --retry 3 "https://github.com/Genymobile/scrcpy/releases/download/v${SCRCPY_VERSION}/scrcpy-linux-x86_64-v${SCRCPY_VERSION}.tar.gz" --output /tmp/scrcpy.tar.gz \
    && echo "${SCRCPY_SHA256}  /tmp/scrcpy.tar.gz" | sha256sum --check --strict \
    && tar -xzf /tmp/scrcpy.tar.gz -C /opt \
    && mv "/opt/scrcpy-linux-x86_64-v${SCRCPY_VERSION}" /opt/scrcpy \
    && rm -f /tmp/platform-tools.zip \
    && rm -f /tmp/scrcpy.tar.gz \
    && apt-get purge -y --auto-remove curl unzip \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/app ./backend/app
COPY --from=frontend-build /src/frontend/dist ./frontend/dist
RUN mkdir -p /app/data/logs \
    && groupadd --system asm \
    && useradd --system --gid asm --home-dir /app --shell /usr/sbin/nologin asm \
    && chown -R asm:asm /app
USER asm
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)"
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
