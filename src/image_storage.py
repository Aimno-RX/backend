# -*- coding: utf-8 -*-
"""
图片存储模块：将 Vision LLM 识别的图片描述写入 Neo4j，并保存图片文件到本地挂载卷。

Neo4j 节点结构：
  (:ExerciseImage {
    id: "文档名_img_004",
    fileName: "文档名.docx",
    imagePath: "文档名/img_004_练习一_起始姿势.png",
    imageUrl: "/api/images/文档名/img_004",
    paragraphIndex: 115,
    exerciseName: "练习一",
    sectionType: "起始姿势",
    description: "Vision LLM 返回的描述",
    startingPosture: "仰卧位",
    movementDescription: "...",
    targetBodyParts: ["颈椎", "背肌"],
    repetitions: "3次",
    precautions: "保持呼吸"
  })
  (:ExerciseImage)-[:BELONGS_TO]->(:Document)
  (:ExerciseImage)-[:ILLUSTRATES]->(:Chunk)
"""

import logging
import os
import re
import hashlib
from typing import List, Dict, Optional, Tuple

from src.shared.common_fn import get_value_from_env

logger = logging.getLogger(__name__)

IMAGE_STORAGE_DIR = get_value_from_env("IMAGE_STORAGE_DIR", "/data/images", "str")


def sanitize_file_name(name: str, max_length: int = 50) -> str:
    """清理文件名中的非法字符和Markdown标记"""
    safe_name = re.sub(r'[\\/:*?"<>|\n\r\t]', '_', name)
    safe_name = re.sub(r'[*#`]+', '', safe_name)
    safe_name = re.sub(r'_+', '_', safe_name).strip('_ ')
    if len(safe_name) > max_length:
        safe_name = safe_name[:max_length].rstrip('_ ')
    return safe_name or "unnamed"


def parse_rehabilitation_description(description: str) -> Dict[str, object]:
    """
    解析 Vision LLM 返回的康复训练图片描述文本。
    从描述中提取结构化字段：训练动作、姿势、动作描述、训练参数、针对部位、注意事项。

    Args:
        description: Vision LLM 返回的描述文本

    Returns:
        包含结构化字段的字典
    """
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
        elif current_key and not line.startswith(('#', '-', '*')):
            if current_key == "targetBodyParts":
                pass
            elif result.get(current_key) and len(result[current_key]) < 500:
                result[current_key] += " " + line.strip(' *')

    return result


def generate_semantic_filename(
    image_index: int,
    paragraph_index: int,
    parsed_desc: Dict,
    extension: str = "png",
) -> str:
    """
    根据图片描述生成语义化文件名。

    格式: img_{index:03d}_p{para}_{exerciseName}_{sectionType}.{ext}
    """
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


def save_image_files(
    file_name: str,
    images: List[Dict],
    image_descriptions: List[Dict],
    output_dir: Optional[str] = None,
) -> List[Dict]:
    """
    保存图片文件到本地挂载卷，文件名包含语义信息。

    Args:
        file_name: 文档名称
        images: extract_images_from_docx 返回的原始图片列表
        image_descriptions: process_document_images 返回的描述列表
        output_dir: 图片保存目录，默认为 IMAGE_STORAGE_DIR/{file_name}/

    Returns:
        包含保存路径信息的字典列表
    """
    if output_dir is None:
        output_dir = os.path.join(IMAGE_STORAGE_DIR, sanitize_file_name(file_name))

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
        image_bytes = img.get("image_bytes", b"")

        if not image_bytes:
            continue

        desc_info = desc_map.get(idx, {})
        description_text = desc_info.get("description", "")

        parsed = parse_rehabilitation_description(description_text)

        semantic_name = generate_semantic_filename(
            image_index=idx,
            paragraph_index=para_idx,
            parsed_desc=parsed,
            extension=ext,
        )

        file_path = os.path.join(output_dir, semantic_name)

        try:
            with open(file_path, 'wb') as f:
                f.write(image_bytes)
            logger.info(f"Saved image: {semantic_name} ({len(image_bytes)} bytes)")
        except Exception as e:
            logger.error(f"Failed to save image {semantic_name}: {e}")
            continue

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

    logger.info(f"Saved {len(saved_paths)} images to {output_dir}")
    return saved_paths


def store_image_nodes(
    graph,
    file_name: str,
    saved_paths: List[Dict],
) -> int:
    """
    将图片描述写入 Neo4j 的 ExerciseImage 节点，并创建与 Document 的关系。

    Args:
        graph: Neo4jGraph 实例
        file_name: 文档名称
        saved_paths: save_image_files 返回的路径信息列表

    Returns:
        成功写入的节点数
    """
    from src.shared.common_fn import execute_graph_query

    if not saved_paths:
        logger.warning("No image paths to store in Neo4j")
        return 0

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

    try:
        execute_graph_query(graph, query, params={"batch_data": batch_data})
        logger.info(f"Stored {len(batch_data)} ExerciseImage nodes in Neo4j")
        return len(batch_data)
    except Exception as e:
        logger.error(f"Failed to store ExerciseImage nodes: {e}")
        return 0


def link_images_to_chunks(
    graph,
    file_name: str,
    saved_paths: List[Dict],
) -> int:
    """
    将 ExerciseImage 节点与对应的 Chunk 节点关联。

    根据 paragraphIndex 和 Chunk 的 position/content_offset 进行匹配。

    Args:
        graph: Neo4jGraph 实例
        file_name: 文档名称
        saved_paths: save_image_files 返回的路径信息列表

    Returns:
        成功创建的关系数
    """
    from src.shared.common_fn import execute_graph_query

    batch_data = []
    for sp in saved_paths:
        para_idx = sp.get("paragraph_index", 0)
        batch_data.append({
            "imageId": f"{file_name}_img_{sp['image_index']:03d}",
            "paragraphIndex": para_idx,
            "fileName": file_name,
        })

    query = """
    UNWIND $batch_data AS data
    MATCH (img:ExerciseImage {id: data.imageId})
    MATCH (c:Chunk {fileName: data.fileName})
    WHERE c.position IS NOT NULL
    WITH img, c, data
    ORDER BY ABS(c.position - data.paragraphIndex) ASC
    WITH img, collect(c)[0] AS nearest_chunk
    MERGE (img)-[:ILLUSTRATES]->(nearest_chunk)
    """

    try:
        execute_graph_query(graph, query, params={"batch_data": batch_data})
        logger.info(f"Linked {len(batch_data)} ExerciseImage nodes to Chunks")
        return len(batch_data)
    except Exception as e:
        logger.error(f"Failed to link images to chunks: {e}")
        return 0


def search_images_by_symptom(
    graph,
    query_text: str,
    limit: int = 5,
) -> List[Dict]:
    """
    根据症状或动作名搜索相关图片（用于 QA 侧）。

    Args:
        graph: Neo4jGraph 实例
        query_text: 查询文本（如"颈椎疼"、"练习一"）
        limit: 返回最大数量

    Returns:
        匹配的图片信息列表
    """
    from src.shared.common_fn import execute_graph_query

    cypher = """
    MATCH (img:ExerciseImage)
    WHERE img.description CONTAINS $query
       OR img.exerciseName CONTAINS $query
       OR img.startingPosture CONTAINS $query
       OR img.targetBodyParts CONTAINS $query
       OR img.movementDescription CONTAINS $query
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
    LIMIT $limit
    """

    try:
        results = execute_graph_query(graph, cypher, params={"query": query_text, "limit": limit})
        return results if results else []
    except Exception as e:
        logger.error(f"Failed to search images: {e}")
        return []