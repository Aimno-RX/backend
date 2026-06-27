# 项目手册 — 医学知识图谱构建与问答系统

> 最后更新：2026-06-27  
> 分支：`fix/backend-chase`  
> 仓库：https://github.com/Aimno-RX/backend

---

## 1. 项目概述

本项目是一个**中文医学康复知识图谱构建与 RAG 问答系统**，基于 Neo4j LLM Graph Builder 深度定制。

核心能力：
- 导入医学文档（DOCX/PDF/网页/维基百科），通过 LLM 提取结构化实体与关系
- 存入 Neo4j 知识图谱，支持 80+ 种医学实体类型、100+ 种关系类型
- RAG 问答：向量检索 + 图谱扩展 + 图片提取
- 多模态：视觉 LLM 自动描述文档中的训练动作图片

---

## 2. 项目架构

```
backend/                           ← 后端 (本仓库)
├── score.py                       ← FastAPI 入口，所有 API 路由
├── Dockerfile                     ← Python 3.10-slim, gunicorn+uvicorn
├── requirements.txt               ← ~199 个 Python 依赖
├── constraints.txt                ← PyTorch CPU wheel 约束
├── .env.example                   ← 环境变量模板
├── static/
│   └── chatbot.html               ← Web 聊天界面
├── src/                           ← 核心源码 (volume 挂载)
│   ├── main.py                    ← 核心：upload / extract / processing_source (1365行)
│   ├── llm.py                     ← LLM 配置 (DeepSeek chat, Qwen VL)
│   ├── QA_integration.py          ← 聊天 QA：检索 + LLM 回答 + 图片提取
│   ├── custom_neo4j_retriever.py  ← 自定义向量检索器 (直接 Cypher + query_vector)
│   ├── graphDB_dataAccess.py      ← Neo4j 数据访问层 (Document/Source CRUD)
│   ├── graph_query.py             ← Neo4j 驱动创建、图/块查询
│   ├── create_chunks.py           ← 文档分块（医学文本优化参数）
│   ├── make_relationships.py      ← 块关系、嵌入、向量索引
│   ├── post_processing.py         ← 后处理：向量/全文索引、实体嵌入、schema 合并、社区检测
│   ├── image_processor.py         ← docx 图片提取 (zipfile+lxml)
│   ├── image_storage.py           ← 图片存盘 + Neo4j ExerciseImage 节点 + 链接 chunk
│   ├── medical_extraction_config.py        ← 80+ 中文医学实体/关系类型 + 提取提示词
│   ├── rehabilitation_extraction_config.py ← 康复专用实体/关系类型
│   ├── rehabilitation_triplet_extractor.py ← 规则三元组提取
│   ├── triplet_enhancement_integration.py  ← 三元组融合管道 (LLM + 规则)
│   ├── entity_optimizer.py        ← 实体清洗、去重、同义词合并
│   ├── communities.py             ← 社区检测 (Graph Data Science)
│   ├── custom_graph_transformer.py← 自定义 LLM 图转换器
│   ├── document_sources/          ← 文档源加载器
│   │   ├── local_file.py          ← 自定义 zipfile+lxml 替代 UnstructuredFileLoader
│   │   ├── local_file_optimized.py
│   │   ├── s3_bucket.py           ← AWS S3
│   │   ├── gcs_bucket.py          ← Google Cloud Storage
│   │   ├── web_pages.py           ← 网页
│   │   └── wikipedia.py           ← 维基百科
│   ├── entities/                  ← Pydantic 数据模型
│   │   ├── source_extract_params.py
│   │   ├── source_node.py
│   │   └── user_credential.py    ← Neo4jCredentials (支持 env 回退)
│   └── shared/                    ← 共用工具
│       ├── constants.py           ← 系统提示词 + Cypher 查询 + 聊天模式配置
│       ├── common_fn.py           ← load_embedding_model 等共用函数
│       ├── schema_extraction.py   ← Schema 提取
│       └── llm_graph_builder_exception.py
└── stress_test.py                 ← 并发压力测试脚本

mp-weixin/                         ← 微信小程序 (uni-app 编译，单独项目)
├── api/qa.js                      ← 聊天 API 调用 + 图片提取
├── pages/tabbar/qa/index.js       ← 聊天页面逻辑 + 图片渲染
├── pages/tabbar/qa/index.wxml     ← 聊天页面模板 (含图片卡片)
└── pages/tabbar/qa/index.wxss     ← 样式 (含图片样式)
```

---

## 3. 技术栈

| 层级 | 技术 |
|---|---|
| Web 框架 | FastAPI 0.129.0 |
| ASGI 服务器 | Gunicorn 23.0.0 + Uvicorn 0.40.0 (UvicornWorker) |
| 图数据库 | Neo4j 5 (neo4j-driver 6.1.0, langchain-neo4j 0.8.0) |
| LLM | DeepSeek (OpenAI 兼容 API), 可选 GPT-4o |
| 视觉 LLM | DeepSeek-VL2, Qwen-VL (图片描述) |
| 向量嵌入 | bge-small-zh-v1.5 (512维, 中文优化) |
| LangChain | langchain 1.2.10 + langgraph 1.0.8 |
| 文档处理 | PyMuPDF, python-docx, zipfile+lxml (自定义) |
| 部署 | Docker (python:3.10-slim), 端口 8000 |
| 评测 | RAGAS |

---

## 4. 服务器部署环境

| 项 | 值 |
|---|---|
| 服务器 | 阿里云, 4GB RAM, 40GB 磁盘 |
| IP | 120.77.179.94 |
| 后端端口 | 8000 |
| 服务器代码路径 | /home/admin/backend/src |
| 测试文件 | /home/admin/test1.docx (39MB, 231页) |
| 内存占用 | ~2.6GB / 4GB |

### Docker 容器

| 容器 | 镜像 | 端口 | Volume 挂载 |
|---|---|---|---|
| test-backend | medical-kg-backend:with-compat | 8000:8000 | -v /home/admin/backend/src:/code/src |
| | | | -v /home/admin/images:/data/images |
| | | | -v /home/admin/nltk_data:/usr/local/nltk_data |
| neo4j | neo4j:5 | 7687:7687 | -v /home/admin/neo4j-data:/data |

### test-backend 启动命令

```bash
docker run -d --name test-backend --restart unless-stopped \
  --network admin_app-network -p 8000:8000 \
  -v /home/admin/backend/src:/code/src \
  -v /home/admin/images:/data/images \
  -v /home/admin/nltk_data:/usr/local/nltk_data \
  -e LLM_MODEL_CONFIG_DEEPSEEK_CHAT="deepseek-chat,https://api.deepseek.com,<YOUR_DEEPSEEK_API_KEY>" \
  -e DEEPSEEK_API_KEY="<YOUR_DEEPSEEK_API_KEY>" \
  --entrypoint bash medical-kg-backend:with-compat \
  -c "pip install pymupdf==1.27.2 -i https://mirrors.aliyun.com/pypi/simple/ --quiet && gunicorn score:app --bind 0.0.0.0:8000 --workers 2 --timeout 600 --worker-class uvicorn.workers.UvicornWorker"
```

### ⚠️ 部署注意事项

**score.py 和 static/ 不在 volume 挂载范围内！**

- `/home/admin/backend/src` → `/code/src` (volume, 自动同步)
- `/home/admin/backend/score.py` → **需要 `docker cp`** 到 `/code/score.py`
- `/home/admin/backend/static/` → **需要 `docker cp`** 到 `/code/static/

---

## 5. 部署流程

```bash
# 1. 本地 commit + push
cd C:\Users\JSJ\Desktop\kangwen\backend
git add <files>
git commit -m "..."
git push origin fix/backend-chase

# 2. 服务器 pull
cd /home/admin/backend && git pull origin fix/backend-chase

# 3. ⚠️ score.py 需要额外 cp (不在 volume 内)
docker cp /home/admin/backend/score.py test-backend:/code/score.py

# 4. 清除 pycache + 重启
docker exec test-backend find /code/src -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
docker restart test-backend

# 5. 验证
docker exec test-backend python -c "import score; print('OK')"
curl http://120.77.179.94:8000/health
```

---

## 6. API 接口一览

### 轻量接口

| 接口 | 方法 | 说明 |
|---|---|---|
| `/health` | GET | 健康检查 |
| `/docs` | GET | Swagger API 文档 |
| `/connect` | POST | 测试 Neo4j 连接 |

### 文档管理

| 接口 | 方法 | 参数类型 | 说明 |
|---|---|---|---|
| `/upload` | POST | Form+File | 分块上传文件 |
| `/url/scan` | POST | Form | 从 URL/S3/GCS/维基创建源节点 |
| `/extract` | POST | Form | 提取知识图谱 |
| `/sources_list` | POST | Form(env) | 列出所有文档源 |
| `/document_status/{file_name}` | GET | Query | 获取文档处理状态 |
| `/update_extract_status/{file_name}` | GET(SSE) | Query | 流式获取提取状态 |
| `/delete_document_and_entities` | POST | Form | 删除文档及实体 |
| `/cancelled_job` | POST | Form | 取消运行中的任务 |
| `/retry_processing` | POST | Form | 重试处理 |

### 聊天问答

| 接口 | 方法 | 参数类型 | 说明 |
|---|---|---|---|
| `/chat_bot` | POST | **Form** | RAG 问答（核心接口） |
| `/clear_chat_bot` | POST | Form | 清除聊天历史 |
| `/chat_queue_status` | GET | - | 排队状态监控 |

### 图谱查询

| 接口 | 方法 | 参数类型 | 说明 |
|---|---|---|---|
| `/graph_query` | POST | Form | 按文档名查询图数据 |
| `/schema` | POST | Form(env) | 获取图谱 schema |
| `/populate_graph_schema` | POST | Form | 从文本提取 schema |
| `/chunk_entities` | POST | Form | 获取 chunk 的实体 |
| `/get_neighbours` | POST | Form | 获取邻居节点 |
| `/schema_visualization` | POST | Form | Schema 可视化 |
| `/fetch_chunktext` | POST | Form | 获取 chunk 文本 |
| `/execute_cypher` | POST | JSON | 执行 Cypher 查询 |

### 图谱维护

| 接口 | 方法 | 参数类型 | 说明 |
|---|---|---|---|
| `/post_processing` | POST | Form | 后处理（索引/社区/相似度） |
| `/drop_create_vector_index` | POST | Form | 重建向量索引 |
| `/get_duplicate_nodes` | POST | JSON | 获取重复节点 |
| `/merge_duplicate_nodes` | POST | JSON | 合并重复节点 |
| `/get_unconnected_nodes_list` | POST | Form(env) | 获取未连接节点 |
| `/delete_unconnected_nodes` | POST | Form | 删除未连接节点 |

### 图片服务

| 接口 | 方法 | 参数类型 | 说明 |
|---|---|---|---|
| `/api/images/{file_name}/{image_id}` | GET | Path | 返回图片文件 |
| `/api/images/search` | POST | JSON | 按症状/部位搜索图片 |
| `/api/images/list` | POST | JSON | 列出文档所有图片 |

### 查询库 & 评测

| 接口 | 方法 | 参数类型 | 说明 |
|---|---|---|---|
| `/query_library` | GET/POST/DELETE | JSON | 自定义 Cypher 查询库 CRUD |
| `/metric` | POST | Form | RAGAS 评测指标 |
| `/chat` | GET | - | Web 聊天界面 |

---

## 7. 核心接口参数详情

### `/chat_bot` (POST, Form)

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| model | string | **是** | LLM 模型名，如 `deepseek_chat` |
| question | string | **是** | 用户问题 |
| document_names | string | **是** | JSON 字符串，如 `["test1.docx"]` |
| session_id | string | **是** | 会话 ID，用于聊天历史 |
| mode | string | 否 | 聊天模式，默认 `graph_vector` |

**聊天模式：**

| 模式 | 说明 |
|---|---|
| `graph_vector` | 向量搜索 + 图扩展 + 图片 (默认，推荐) |
| `graph_vector_fulltext` | 向量 + 全文 + 图扩展 |
| `vector` | 纯向量搜索 |
| `fulltext` | 纯全文搜索 |
| `graph` | 纯图谱 Cypher 查询 |
| `entity_vector` | 实体嵌入 + 本地社区扩展 |
| `global_vector` | 社区级全局搜索 |

**响应示例：**
```json
{
  "status": "Success",
  "data": {
    "session_id": "xxx",
    "message": "建议进行颈部肌肉强化训练...",
    "info": {
      "sources": ["test1.docx"],
      "model": "deepseek-chat",
      "total_tokens": 4703,
      "response_time": 5.2,
      "queue_wait_time": 0.0,
      "mode": "graph_vector",
      "entities": [...],
      "images": [{"imageUrl": "/api/images/test1.docx/img_000", ...}]
    }
  }
}
```

### `/extract` (POST, Form)

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| model | string | 是 | LLM 模型 |
| file_name | string | 是 | 文件名 |
| source_type | string | 是 | `local file` / `s3 bucket` / `web-url` / `Wikipedia` |
| retry_condition | string | 否 | 重试条件 |

---

## 8. Chat Bot 并发控制（请求排队机制）

### 原理

```
请求进来 → 信号量有空位？ → 是 → 立即处理
                      → 否 → 排队等待（最多120秒）
                              → 有空位 → 处理
                              → 超时 → 返回 "Server busy"（不断连）
```

### 配置项

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `CHAT_MAX_CONCURRENT` | `8` | 同时处理的最大 chat_bot 请求数 |
| `CHAT_QUEUE_TIMEOUT` | `120` | 排队等待超时秒数 |

### 监控接口

`GET /chat_queue_status`
```json
{
  "active_requests": 5,
  "max_concurrent": 8,
  "available_slots": 3,
  "queue_timeout_seconds": 120,
  "utilization_percent": 62.5
}
```

### 压力测试结果（加排队前）

| 并发数 | 成功率 | 平均耗时 | 状态 |
|:---:|:---:|:---:|:---:|
| 1 | 100% | 5.1s | 正常 |
| 3 | 100% | 5.9s | 正常 |
| 5 | 100% | 8.5s | 正常 |
| 10 | 80% | 14.6s | 有断连 |
| 15 | 70.7% | 20.2s | 大量断连 |
| 20 | 57.5% | 23.3s | 严重断连 |
| 30 | 54.7% | 30.8s | 严重断连 |
| 40 | 41.0% | 33.8s | 接近崩溃 |

**安全并发上限：5 个同时设备**（不加排队时）  
**加排队后：50 个同时请求全部成功**（排队等 0~30 秒）

---

## 9. Neo4j 数据模型

```
(Document {fileName, status, nodeCount, model, processingTime, token_usage})
    ↓ PART_OF / FIRST_CHUNK
(Chunk {text, position, embedding, fileName, page_number})
    ↓ NEXT_CHUNK → (Chunk)
    ↓ HAS_ENTITY → (__Entity__ {id, description, embedding, type-specific labels})
    ↓ SIMILAR → (Chunk) [KNN similarity]

(ExerciseImage {id, imageUrl, exerciseName, description, startingPosture,
                movementDescription, targetBodyParts, paragraphIndex})
    ↓ BELONGS_TO → (Document)
    ↓ ILLUSTRATES → (Chunk)

(__Community__ {summary, communityRank, weight, embedding})
    ↓ IN_COMMUNITY ← (__Entity__)
    ↓ PARENT_COMMUNITY → (__Community__) [hierarchical]
```

**当前数据状态：**

| 指标 | 值 |
|---|---|
| Document | test1.docx, status=Completed |
| 总节点数 | 2517 |
| 总关系数 | 20950 |
| Chunks | 523, 全部有 embedding (bge-small-zh-v1.5, 512维) |
| Entities | 2096 |
| Entity关系 | 6346 |
| ExerciseImage | 236, 全部有 ILLUSTRATES 关系 |
| 图片覆盖 | 120/523 chunk 有图片链接 (±5 位置窗口) |

---

## 10. 核心数据流

```
文档上传 (/upload)
    ↓
文档分块 (TokenTextSplitter, 医学优化参数)
    ↓
嵌入生成 (bge-small-zh-v1.5)
    ↓
LLM 实体/关系提取 (DeepSeek, 80+ 实体类型)
    ↓
规则三元组提取 (rehabilitation_triplet_extractor)
    ↓
三元组融合 & 去重 (triplet_enhancement_integration)
    ↓
实体优化 (清洗/同义词合并/类型归一化)
    ↓
存入 Neo4j 知识图谱
    ↓
图片提取 & 视觉 LLM 描述 (Qwen-VL/DeepSeek-VL2)
    ↓
图片存储 + ExerciseImage 节点 + ILLUSTRATES 链接
    ↓
后处理 (向量索引/全文索引/社区检测/schema合并)
    ↓
RAG 问答服务 (/chat_bot)
```

---

## 11. 医学领域实体类型

### 临床基础
疾病、症状、体征、解剖部位、治疗方法、药物、检查项目、病因、并发症、病理变化

### 疼痛机制
疼痛类型、疼痛机制、伤害性感受器、神经纤维、神经通路、脑区、脊髓层

### 炎症/神经化学
炎症介质、细胞因子、神经递质、内源性物质、生物标志物

### 敏化
敏化类型、敏化机制、感觉异常、疼痛现象

### 心理
心理因素、心理状态、神经内分泌轴、应激反应

### 康复训练
训练动作、频次、姿势、效果、强度、注意事项、肌肉群、起始姿势、动作要领、重复次数、训练强度、训练频率、训练周期、组数、次数、持续时间、休息时间

### 康复专有
训练目标、功能改善、症状缓解、预防效果、禁忌症、风险因素、安全指导、康复阶段、急性期、亚急性期、慢性期、恢复期

---

## 12. 常用调试命令

```bash
# === 容器管理 ===
docker ps                          # 查看运行容器
docker logs test-backend --tail 50 # 查看后端日志
docker restart test-backend        # 重启后端
docker exec test-backend python -c "import score; print('OK')"  # 验证代码

# === Neo4j 数据 ===
docker exec neo4j cypher-shell -u neo4j -p <password> "MATCH (n) RETURN count(n)"
docker exec neo4j cypher-shell -u neo4j -p <password> "MATCH (n:Document) RETURN n.fileName, n.status"
docker exec neo4j cypher-shell -u neo4j -p <password> "MATCH (n:ExerciseImage) RETURN count(n)"

# === 接口测试 ===
curl http://120.77.179.94:8000/health
curl -X POST http://120.77.179.94:8000/chat_queue_status

# === 排队监控 ===
curl http://120.77.179.94:8000/chat_queue_status

# === 清理 ===
docker exec test-backend find /code/src -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

# === 部署更新 (score.py 不在 volume 内) ===
docker cp /home/admin/backend/score.py test-backend:/code/score.py
docker restart test-backend
```

---

## 13. 潜在优化项

| 问题 | 说明 | 优先级 |
|---|---|---|
| 图片描述字段过长 | Qwen VL 输出了完整分析推理文本，exerciseName 应清洗为动作名 | 高 |
| 图片链接只覆盖 23% chunk | ±5 位置窗口链接了 120/523 chunk，其余 chunk 无图 | 中 |
| score.py 不在 volume | 每次改 score.py 需 docker cp，容易忘记，建议加 volume 或放 src/ | 中 |
| 只支持 .docx | PDF 等格式不支持 | 中 |
| Gunicorn workers=2 | 高并发可能不够（已加排队机制缓解） | 低 |
| Neo4j 内存 | 1G heap + 256m pagecache，大文档可能 OOM | 低 |
| push 经常超时 | GitHub 连接不稳定，需重试 | 低 |
| embedding 模型加载慢 | 每次启动重新加载 bge-small-zh-v1.5 | 低 |
| ExerciseImage 节点名固化 | 通用文档不适合，应改为 DocumentImage | 低 |
| Vision LLM 提示词定制 | 目前针对康复训练，换文档类型需改提示词 | 低 |
| 无 PDF 图片提取 | 需添加 pymupdf/pdfplumber 支持 | 低 |

---

## 14. 压力测试

压力测试脚本位于 `stress_test.py`，使用方法：

```bash
# 安装依赖
pip install aiohttp

# 运行测试（逐步增加并发：1,3,5,10,15,20,30,40,50）
PYTHONUTF8=1 python stress_test.py
```

可修改脚本中的 `CONCURRENCY_LEVELS` 和 `REQUESTS_PER_LEVEL` 调整测试参数。
