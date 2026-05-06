FROM python:3.10-slim

WORKDIR /code

ENV PORT=8000 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=300 \
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
        --constraint /code/constraints.txt \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        -r /code/requirements.txt && \
    rm -rf /root/.cache/pip

RUN python -m nltk.downloader -d /usr/local/nltk_data punkt && \
    python -m nltk.downloader -d /usr/local/nltk_data averaged_perceptron_tagger && \
    python -m nltk.downloader -d /usr/local/nltk_data punkt_tab

COPY . /code/


RUN sed -i 's/from langchain_classic\.retrievers/from langchain.retrievers/g' /code/src/QA_integration.py && \
    sed -i 's/from langchain_classic\.retrievers\.document_compressors/from langchain.retrievers.document_compressors/g' /code/src/QA_integration.py && \
    sed -i 's/from langchain_huggingface/from langchain_community.embeddings/g' /code/src/shared/common_fn.py && \
    sed -i 's/from langchain_google_vertexai/from langchain_community.embeddings/g' /code/src/shared/common_fn.py
 


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