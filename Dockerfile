FROM python:3.12-slim

WORKDIR /code

ENV PORT=8000 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

EXPOSE 8000

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libmagic1 \
        libgl1 \
        libglib2.0-0 \
        libglx-mesa0 \
        libgomp1 \
        libreoffice \
        poppler-utils \
        tesseract-ocr \
        cmake \
        gcc \
        g++ \
        git \
        curl \
        wget && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY constraints.txt /code/
COPY requirements.txt /code/

RUN pip install --upgrade pip setuptools wheel && \
    pip install \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        "torch==2.3.1+cpu" \
        "torchvision==0.18.1+cpu" \
        "torchaudio==2.3.1+cpu" && \
    grep -v '^-f ' /code/constraints.txt > /tmp/constraints_clean.txt && \
    pip install \
        --constraint /tmp/constraints_clean.txt \
        -r /code/requirements.txt \
        --extra-index-url https://download.pytorch.org/whl/cpu && \
    rm -rf /root/.cache/pip /tmp/constraints_clean.txt

RUN python -m nltk.downloader -d /usr/local/nltk_data punkt && \
    python -m nltk.downloader -d /usr/local/nltk_data averaged_perceptron_tagger && \
    python -m nltk.downloader -d /usr/local/nltk_data punkt_tab

COPY . /code/

RUN mkdir -p /code/chunks /code/merged_files /code/local_model && \
    chmod -R 755 /code

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["gunicorn", "score:app", \
     "--workers", "2", \
     "--threads", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "300", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]