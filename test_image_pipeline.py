# -*- coding: utf-8 -*-
"""
测试图片抽取+识别+存储全流程：仅处理前5张图片
用法: python test_image_pipeline.py
"""

import base64
import logging
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

DOCX_PATH = r"E:\xwechat_files\wxid_kngvfm4spkj422_1a7f\msg\file\2026-06\《颈椎胸椎功能强化训练》已整理完毕.docx"
FILE_NAME = "《颈椎胸椎功能强化训练》已整理完毕.docx"
MAX_IMAGES = 5


# ─── 内联工具函数（避免深层依赖） ───

def sanitize_file_name(name, max_length=50):
    safe_name = re.sub(r'[\\/:*?"<>|\n\r\t]', '_', name)
    safe_name = re.sub(r'[*#`]+', '', safe_name)
    safe_name = re.sub(r'_+', '_', safe_name).strip('_ ')
    if len(safe_name) > max_length:
        safe_name = safe_name[:max_length].rstrip('_ ')
    return safe_name or "unnamed"


def parse_rehabilitation_description(description):
    result = {
        "exerciseName": "",
        "startingPosture": "",
        "movementDescription": "",
        "repetitions": "",
        "targetBodyParts": [],
        "precautions": "",
    }
    if not description:
        return result
    lines = description.split('\n')
    current_key = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        line = re.sub(r'^#{1,6}\s*', '', line)
        line = re.sub(r'^[\d]+\.\s*\*{0,2}', '', line)
        line = re.sub(r'\*{0,2}[:：]\*{0,2}', ':', line)
        line = line.strip('* ')
        if not line:
            continue
        lower = line.lower()
        if any(k in lower for k in ['训练动作', 'exercise name', 'exercise']):
            content = re.sub(r'^[^:：]*[:：]\s*', '', line).strip()
            result["exerciseName"] = content.strip(' *')
            current_key = "exerciseName"
        elif any(k in lower for k in ['姿势', 'posture', '起始姿势', '体位', 'starting']):
            content = re.sub(r'^[^:：]*[:：]\s*', '', line).strip()
            result["startingPosture"] = content.strip(' *')
            current_key = "startingPosture"
        elif any(k in lower for k in ['动作描述', 'movement', '动作要领', '动作']):
            content = re.sub(r'^[^:：]*[:：]\s*', '', line).strip()
            result["movementDescription"] = content.strip(' *')
            current_key = "movementDescription"
        elif any(k in lower for k in ['训练参数', 'repetitions', '重复', '频次', '次数']):
            content = re.sub(r'^[^:：]*[:：]\s*', '', line).strip()
            result["repetitions"] = content.strip(' *')
            current_key = "repetitions"
        elif any(k in lower for k in ['针对部位', 'target', '部位', '肌', '关节']):
            content = re.sub(r'^[^:：]*[:：]\s*', '', line).strip()
            parts = [p.strip(' *') for p in re.split(r'[,，、；;]', content) if p.strip(' *')]
            result["targetBodyParts"] = parts
            current_key = "targetBodyParts"
        elif any(k in lower for k in ['注意', 'precaution', '安全', 'warning']):
            content = re.sub(r'^[^:：]*[:：]\s*', '', line).strip()
            result["precautions"] = content.strip(' *')
            current_key = "precautions"
        elif current_key and current_key != "targetBodyParts" and not line.startswith(('#', '-', '*')):
            if result.get(current_key) and len(result[current_key]) < 500:
                result[current_key] += " " + line.strip(' *')
    return result


def generate_semantic_filename(image_index, paragraph_index, parsed_desc, extension="png"):
    parts = [f"img_{image_index:03d}_p{paragraph_index}"]
    exercise = parsed_desc.get("exerciseName", "")
    section = parsed_desc.get("startingPosture", "")
    if exercise:
        parts.append(sanitize_file_name(exercise, 20))
    if section:
        parts.append(sanitize_file_name(section, 15))
    name = "_".join(parts)
    if extension == "x-emf":
        extension = "emf"
    return f"{name}.{extension}"


def save_image_files_inline(file_name, images, image_descriptions, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    desc_map = {}
    for desc in image_descriptions:
        idx = desc.get("image_index", desc.get("index", -1))
        desc_map[idx] = desc

    saved_paths = []
    for img in images:
        idx = img.get("index", 0)
        para_idx = img.get("paragraph_index", 0)
        ext = img.get("extension", "png")
        image_bytes = img.get("original_bytes", img.get("image_bytes", b""))
        if not image_bytes:
            continue

        desc_info = desc_map.get(idx, {})
        description_text = desc_info.get("description", "")
        parsed = parse_rehabilitation_description(description_text)
        semantic_name = generate_semantic_filename(idx, para_idx, parsed, ext)
        file_path = os.path.join(output_dir, semantic_name)

        with open(file_path, 'wb') as f:
            f.write(image_bytes)
        logger.info(f"  保存: {semantic_name} ({len(image_bytes)}B)")

        relative_path = os.path.join(sanitize_file_name(file_name), semantic_name)
        saved_paths.append({
            "image_index": idx,
            "paragraph_index": para_idx,
            "semantic_filename": semantic_name,
            "absolute_path": file_path,
            "relative_path": relative_path,
            "image_url": f"/api/images/{sanitize_file_name(file_name)}/img_{idx:03d}",
            "file_size": len(image_bytes),
            "extension": ext,
            "parsed_description": parsed,
            "raw_description": description_text,
        })

    logger.info(f"保存了 {len(saved_paths)} 个图片文件到 {output_dir}")
    return saved_paths


def store_image_nodes_neo4j(uri, username, password, database, file_name, saved_paths):
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(uri, auth=(username, password))
    batch_data = []
    for sp in saved_paths:
        parsed = sp.get("parsed_description", {})
        target_parts = parsed.get("targetBodyParts", [])
        if isinstance(target_parts, list):
            target_parts_str = ", ".join(target_parts)
        else:
            target_parts_str = str(target_parts)
        batch_data.append({
            "id": f"{file_name}_img_{sp['image_index']:03d}",
            "fileName": file_name,
            "imagePath": sp.get("relative_path", ""),
            "imageUrl": sp.get("image_url", ""),
            "imageIndex": sp["image_index"],
            "paragraphIndex": sp.get("paragraph_index", 0),
            "semanticFilename": sp.get("semantic_filename", ""),
            "fileSize": sp.get("file_size", 0),
            "extension": sp.get("extension", ""),
            "description": sp.get("raw_description", ""),
            "exerciseName": parsed.get("exerciseName", ""),
            "startingPosture": parsed.get("startingPosture", ""),
            "movementDescription": parsed.get("movementDescription", ""),
            "repetitions": parsed.get("repetitions", ""),
            "targetBodyParts": target_parts_str,
            "precautions": parsed.get("precautions", ""),
        })

    query = """
    UNWIND $batch_data AS data
    MERGE (img:ExerciseImage {id: data.id})
    SET img.fileName = data.fileName,
        img.imagePath = data.imagePath,
        img.imageUrl = data.imageUrl,
        img.imageIndex = data.imageIndex,
        img.paragraphIndex = data.paragraphIndex,
        img.semanticFilename = data.semanticFilename,
        img.fileSize = data.fileSize,
        img.extension = data.extension,
        img.description = data.description,
        img.exerciseName = data.exerciseName,
        img.startingPosture = data.startingPosture,
        img.movementDescription = data.movementDescription,
        img.repetitions = data.repetitions,
        img.targetBodyParts = data.targetBodyParts,
        img.precautions = data.precautions
    WITH data, img
    MATCH (d:Document {fileName: data.fileName})
    MERGE (img)-[:BELONGS_TO]->(d)
    """

    with driver.session(database=database) as session:
        result = session.run(query, batch_data=batch_data)
        summary = result.consume()
        logger.info(f"  Neo4j 写入: {summary.counters.nodes_created} nodes created, "
                     f"{summary.counters.relationships_created} relationships created, "
                     f"{summary.counters.properties_set} properties set")

    query2 = """
    UNWIND $batch_data AS data
    MATCH (img:ExerciseImage {id: data.imageId})
    MATCH (c:Chunk {fileName: data.fileName})
    WHERE c.position IS NOT NULL
    WITH img, c, data
    ORDER BY ABS(c.position - data.paragraphIndex) ASC
    WITH img, collect(c)[0] AS nearest_chunk
    MERGE (img)-[:ILLUSTRATES]->(nearest_chunk)
    """

    batch_data2 = []
    for sp in saved_paths:
        batch_data2.append({
            "imageId": f"{file_name}_img_{sp['image_index']:03d}",
            "paragraphIndex": sp.get("paragraph_index", 0),
            "fileName": file_name,
        })

    with driver.session(database=database) as session:
        result = session.run(query2, batch_data=batch_data2)
        summary = result.consume()
        logger.info(f"  ILLUSTRATES 关系: {summary.counters.relationships_created} created")

    driver.close()
    return len(batch_data), len(batch_data2)


def search_images_neo4j(uri, username, password, database, query_text, limit=5):
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(uri, auth=(username, password))
    cypher = """
    MATCH (img:ExerciseImage)
    WHERE img.description CONTAINS $qtext
       OR img.exerciseName CONTAINS $qtext
       OR img.startingPosture CONTAINS $qtext
       OR img.targetBodyParts CONTAINS $qtext
       OR img.movementDescription CONTAINS $qtext
    RETURN img.id AS id,
           img.imagePath AS imagePath,
           img.imageUrl AS imageUrl,
           img.exerciseName AS exerciseName,
           img.description AS description,
           img.startingPosture AS startingPosture,
           img.targetBodyParts AS targetBodyParts,
           img.repetitions AS repetitions,
           img.precautions AS precautions,
           img.paragraphIndex AS paragraphIndex
    LIMIT $max_results
    """

    with driver.session(database=database) as session:
        result = session.run(cypher, qtext=query_text, max_results=limit)
        records = [dict(record) for record in result]

    driver.close()
    return records


# ─── 主流程 ───

def main():
    logger.info("=" * 60)
    logger.info("图片抽取+识别+存储 全流程测试 (前5张)")
    logger.info("=" * 60)

    neo4j_uri = os.getenv("NEO4J_URI", "bolt://120.77.179.94:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_pass = os.getenv("NEO4J_PASSWORD", "password")
    neo4j_db = os.getenv("NEO4J_DATABASE", "neo4j")

    # Step 1: 提取图片
    logger.info(f"=== Step 1: 提取前 {MAX_IMAGES} 张图片 ===")
    from src.image_processor import extract_images_from_document

    images, source_type = extract_images_from_document(DOCX_PATH, ".docx", max_total=MAX_IMAGES)
    logger.info(f"提取到 {len(images)} 张图片 (source_type={source_type})")
    for img in images:
        ext = img.get("extension", "?")
        para = img.get("paragraph_index", "?")
        size = len(img.get("image_bytes", b""))
        orig_size = len(img.get("original_bytes", b""))
        idx = img.get("index", "?")
        logger.info(f"  img[{idx}] para={para} ext={ext} resized={size}B original={orig_size}B")

    if not images:
        logger.error("未提取到图片，终止测试")
        return

    # Step 2: Vision模型识别
    logger.info("=== Step 2: 调用 Vision 模型识别图片 ===")
    env_value = os.getenv("LLM_MODEL_CONFIG_qwen_vl", "")
    if not env_value:
        logger.error("LLM_MODEL_CONFIG_qwen_vl 未配置")
        return
    model_name, api_endpoint, api_key = env_value.split(",")
    from langchain_openai import ChatOpenAI
    vision_llm = ChatOpenAI(
        api_key=api_key, base_url=api_endpoint, model=model_name,
        temperature=0, max_tokens=2048, request_timeout=120,
    )
    logger.info(f"Vision LLM: {model_name}")

    from src.image_processor import encode_image_to_base64, describe_image

    descriptions = []
    for img in images:
        idx = img.get("index", 0)
        ext = img.get("extension", "png")
        para = img.get("paragraph_index", 0)

        if ext == "x-emf":
            logger.warning(f"  ⏭ img[{idx}] EMF格式，跳过")
            continue

        b64 = encode_image_to_base64(img["image_bytes"])
        logger.info(f"  识别 img[{idx}] (para={para}, ext={ext}) ...")
        desc = describe_image(
            vision_llm=vision_llm, base64_image=b64, image_format=ext,
            page_context="颈椎胸椎功能强化训练康复训练文档",
            page_number=para, image_index=idx, description_mode="rehabilitation",
        )
        if desc:
            logger.info(f"  ✅ img[{idx}] 描述 ({len(desc)}字): {desc[:120]}...")
            descriptions.append({"description": desc, "image_index": idx, "paragraph_index": para})
        else:
            logger.warning(f"  ❌ img[{idx}] 识别失败")

    logger.info(f"成功识别 {len(descriptions)} 张图片")
    if not descriptions:
        logger.error("未获得图片描述，跳过后续步骤")
        return

    # Step 3: 解析描述 + 保存文件
    logger.info("=== Step 3: 解析描述 + 保存图片文件 ===")
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_output_images", sanitize_file_name(FILE_NAME))
    saved_paths = save_image_files_inline(FILE_NAME, images, descriptions, output_dir)

    for sp in saved_paths:
        parsed = sp.get("parsed_description", {})
        logger.info(
            f"  img[{sp['image_index']}] -> {sp['semantic_filename']} "
            f"({sp['file_size']}B) "
            f"exerciseName='{parsed.get('exerciseName', '')}' "
            f"startingPosture='{parsed.get('startingPosture', '')}' "
            f"targetBodyParts={parsed.get('targetBodyParts', [])}"
        )

    # Step 4: 写入Neo4j
    logger.info("=== Step 4: 写入 Neo4j ExerciseImage 节点 ===")
    stored, linked = store_image_nodes_neo4j(
        neo4j_uri, neo4j_user, neo4j_pass, neo4j_db, FILE_NAME, saved_paths
    )
    logger.info(f"  写入 {stored} 个 ExerciseImage 节点")
    logger.info(f"  创建 {linked} 个 ILLUSTRATES 关系")

    # Step 5: 搜索验证
    logger.info("=== Step 5: 搜索验证 ===")
    for q in ["颈椎", "练习", "仰卧"]:
        results = search_images_neo4j(neo4j_uri, neo4j_user, neo4j_pass, neo4j_db, q, limit=5)
        logger.info(f"  搜索 '{q}': 找到 {len(results)} 个结果")
        for r in results:
            logger.info(f"    id={r['id']} name={r['exerciseName']} posture={r['startingPosture']}")

    # 汇总
    logger.info("=" * 60)
    logger.info("✅ 全流程测试完成!")
    logger.info(f"  提取图片: {len(images)} (含 {sum(1 for i in images if i.get('extension')=='x-emf')} EMF 跳过)")
    logger.info(f"  识别描述: {len(descriptions)}")
    logger.info(f"  保存文件: {len(saved_paths)}")
    logger.info(f"  Neo4j节点: {stored}")
    logger.info(f"  Chunk关联: {linked}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()