# ============================================
# LLM Graph Builder - Backend Dockerfile
# 用于构建知识图谱的后端服务
# ============================================

FROM python:3.12-slim

# 设置工作目录
WORKDIR /code

# 环境变量配置
ENV PORT=8000 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

# 暴露端口
EXPOSE 8000

# 安装系统依赖（单层优化，减少镜像大小）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        # 文件类型识别
        libmagic1 \
        # OpenGL 和图形处理
        libgl1 \
        libglib2.0-0 \
        libglx-mesa0 \
        libgomp1 \
        # 文档处理工具
        libreoffice \
        poppler-utils \
        tesseract-ocr \
        # 编译工具
        cmake \
        gcc \
        g++ \
        # 版本控制
        git \
        # 网络工具
        curl \
        wget && \
    # 清理缓存，减少镜像大小
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# -------------------------------------------------------
# 第一步：单独安装 PyTorch CPU 版本
# constraints.txt 中指定了特殊的 --find-links 源，
# 需要先单独处理，避免 pip 解析冲突
# -------------------------------------------------------
COPY constraints.txt /code/
RUN pip install --upgrade pip setuptools wheel && \
    pip install \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        "torch==2.3.1+cpu" \
        "torchvision==0.18.1+cpu" \
        "torchaudio==2.3.1+cpu" && \
    rm -rf /root/.cache/pip

# -------------------------------------------------------
# 第二步：安装其余 Python 依赖
# 使用 --constraint 而非 -c，跳过 torch 相关的 -f 行
# -------------------------------------------------------
COPY requirements.txt /code/
# 生成过滤掉 -f/--find-links 行的 constraints 文件，供 pip -c 使用
RUN grep -v '^-f ' /code/constraints.txt > /tmp/constraints_clean.txt ; \
    pip install \
        --constraint /tmp/constraints_clean.txt \
        -r /code/requirements.txt \
        --extra-index-url https://download.pytorch.org/whl/cpu && \
    rm -rf /root/.cache/pip /tmp/constraints_clean.txt

# -------------------------------------------------------
# 第三步：下载并缓存预训练模型
# 如果宿主机 ./backend/local_model 已有模型文件，
# docker-compose 会通过 bind mount 覆盖此目录，跳过下载
# -------------------------------------------------------
# 用独立脚本下载模型，避免 python -c 多行字符串中的 'from' 被
# Docker 解析器误识别为 FROM 指令
COPY download_model.py /tmp/download_model.py
RUN python /tmp/download_model.py && \
    rm /tmp/download_model.py && \
    rm -rf /root/.cache/huggingface

# 下载 NLTK 数据
RUN python -m nltk.downloader -d /usr/local/nltk_data punkt && \
    python -m nltk.downloader -d /usr/local/nltk_data averaged_perceptron_tagger && \
    python -m nltk.downloader -d /usr/local/nltk_data punkt_tab && \
    echo "NLTK data downloaded"

# 复制应用代码（排除内容见 .dockerignore）
COPY . /code/

# 创建必要的目录并设置权限
RUN mkdir -p /code/chunks /code/merged_files /code/local_model && \
    chmod -R 755 /code

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
# workers=4，threads=4，适合 IO 密集型 LLM 调用
# timeout=300 秒，兼容长时间 LLM 推理请求
CMD ["gunicorn", "score:app", \
     "--workers", "4", \
     "--threads", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "300", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]
