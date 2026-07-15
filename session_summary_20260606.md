# Session 总结 - 2026-06-06

## 项目：LLM Graph Builder - 本地环境搭建与知识图谱抽取

---

## 1. 环境搭建

### Neo4j 连接
- 服务器地址：`bolt://120.77.179.94:7687`
- 数据库：`neo4j`，用户名/密码：`neo4j` / `password`
- .env 文件路径：`C:\Users\JSJ\Desktop\backend-fix-backend-chase\.env`

### 依赖安装
- 修正 `requirements.txt` 中 torch 版本号（去掉 `+cpu` 后缀）
- 安装核心包：fastapi, uvicorn, langchain, neo4j, torch, sentence-transformers 等
- 补充安装：graphdatascience, boto3, google-cloud-*, chardet, fastapi-health, sse-starlette 等

### 嵌入模型修复
- `src/shared/common_fn.py` 的 `load_embedding_model()` 缺少 `sentence_transformer` 分支
- 新增分支调用 `get_local_sentence_transformer_embedding()`，维度 384
- 下载模型 `all-MiniLM-L6-v2` 到 `./local_model/`

### 代码修复
- `src/main.py:446` — `extract_graph_from_file_Wikipedia` 函数定义被注释掉，已取消注释
- `score.py` — 补充导入 `extract_graph_from_file_Wikipedia`

---

## 2. 服务启动

```bash
python -m uvicorn score:app --host 0.0.0.0 --port 8000
```
- FastAPI 入口：`score.py`（不是 `src/main.py`）
- Swagger 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`

---

## 3. 知识图谱抽取

### 接口
| 接口 | 方法 | 说明 |
|------|------|------|
| `/upload` | POST (multipart) | 上传文档 |
| `/extract` | POST (form) | 抽取知识图谱 |
| `/sources_list` | POST | 查看文档状态 |

### `/upload` 参数
- `file` — 文件
- `chunkNumber`, `totalChunks` — 分块（单文件填 1/1）
- `originalname` — 原始文件名
- `model` — `deepseek_chat`

### `/extract` 参数
- `file_name`, `source_type`=`local file`, `model`=`deepseek_chat`
- `language` — 中文填 `zh`
- `retry_condition`=`start_from_last_processed_position` — 断点续传

### 抽取结果
**文档：《颈椎胸椎功能强化训练》已整理完毕.docx**
- 大小：39.5MB，260 个文本块
- 实体节点：1,611
- 关系：10,158
- 处理时间：~13.6 分钟
- Token 消耗：640,575

**Neo4j 数据库总览（5 篇文档）：**
- 总节点：~25,000+
- 总关系：~45,000+

---

## 4. 图片提取

使用 `src/image_processor.py` 的 `extract_images_from_docx()`：
- 从 DOCX 提取 200 张图片到 `extracted_images/`
- 小图（30-55KB PNG）：训练动作示意图
- 大图（200-220KB PNG）：章节标题
- 矢量图（1.3MB EMF）：3 张大插图

---

## 5. 视觉识别状态

- 当前 LLM：`deepseek-chat`（纯文本，不支持图片）
- `VISION_MODEL` 未配置
- 视觉模型需在 `.env` 中设置 `VISION_MODEL=模型名` 和 `LLM_MODEL_CONFIG_{模型名}=模型名,API地址,API_KEY`

### 后续可做
1. 配置 DeepSeek 或其他视觉模型（如 `deepseek-vl2`）
2. 用 Vision LLM 识别训练动作图片 → 写入图谱
3. 通过 QA 接口查询康复训练方案

---

## 6. 未修复的问题（来自代码审查）
1. `score.py:736` — `uri=url` 应为 `uri=uri`（空格 URL 会失败）
2. `QA_integration.py:578-614` — `model_version` 可能未定义
3. `score.py:293-315` — `merged_file_path` 可能未定义
4. `dbtest.py:9` — 硬编码 Neo4j 密码
5. `locustperf.py:33-50` — 重复 `get_request` 方法
6. `QA_integration.py:39-50` — 无锁的 `history_dict`
7. `main.py:63-88` — `sanitize_uploaded_fileName` 是空操作
