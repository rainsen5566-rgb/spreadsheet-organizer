FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    SOFFICE_PATH=/usr/bin/soffice PDF_WORK_DIR=/tmp/pdf-jobs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-calc fontconfig fonts-noto-cjk fonts-liberation \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 converter
WORKDIR /app
COPY requirements-cloud.txt .
RUN pip install --no-cache-dir -r requirements-cloud.txt
COPY server.py wsgi.py ./
USER converter
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 1 --timeout 300 --max-requests 100 --worker-tmp-dir /tmp wsgi:application"]
