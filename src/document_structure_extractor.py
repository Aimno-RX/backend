# -*- coding: utf-8 -*-
"""
文档结构提取器
负责把文本拆分为段落、句子，并构建结构化文档对象
"""

import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class SentenceUnit:
    """句子单元"""
    sentence_id: str
    text: str
    page_number: int = 1
    paragraph_id: str = ""
    order_in_paragraph: int = 0
    labels: List[str] = field(default_factory=list)


@dataclass
class ParagraphUnit:
    """段落单元"""
    paragraph_id: str
    text: str
    page_number: int = 1
    order_in_page: int = 0
    sentences: List[SentenceUnit] = field(default_factory=list)


@dataclass
class DocumentStructure:
    """结构化文档对象"""
    file_name: str
    paragraphs: List[ParagraphUnit] = field(default_factory=list)
    sentences: List[SentenceUnit] = field(default_factory=list)


def split_page_into_paragraphs(page_text: str) -> List[str]:
    """
    把一页文本拆成多个段落
    优先按空行切分；如果没有明显空行，则保留整个文本块
    """
    if not page_text:
        return []

    text = re.sub(r"\r\n?", "\n", page_text).strip()
    if not text:
        return []

    parts = re.split(r"\n\s*\n+", text)

    cleaned_parts = []
    for part in parts:
        value = re.sub(r"\n+", "\n", part).strip()
        if value:
            cleaned_parts.append(value)

    if cleaned_parts:
        return cleaned_parts

    return [text]


def split_paragraph_into_sentences(paragraph_text: str) -> List[str]:
    """
    把一个段落拆成多个句子
    按中文句号、问号、叹号、分号切分
    """
    if not paragraph_text:
        return []

    text = re.sub(r"\s+", " ", paragraph_text).strip()
    if not text:
        return []

    parts = re.split(r"(?<=[。！？；])\s*", text)
    return [part.strip() for part in parts if part and part.strip()]


def build_document_structure(file_name: str, pages: list) -> DocumentStructure:
    """
    从 pages 构建结构化文档
    pages 中每个元素应至少有:
    - page_content
    - metadata
    """
    structure = DocumentStructure(file_name=file_name)
    paragraph_counter = 1

    for page_index, page in enumerate(pages, start=1):
        page_text = getattr(page, "page_content", "") or ""
        metadata = getattr(page, "metadata", {}) or {}
        page_number = metadata.get("page_number", page_index)

        paragraph_texts = split_page_into_paragraphs(page_text)

        for paragraph_order, paragraph_text in enumerate(paragraph_texts, start=1):
            paragraph_id = f"p{paragraph_counter}"
            paragraph_counter += 1

            sentence_texts = split_paragraph_into_sentences(paragraph_text)
            sentence_units = []

            for sentence_order, sentence_text in enumerate(sentence_texts, start=1):
                sentence_unit = SentenceUnit(
                    sentence_id=f"{paragraph_id}_s{sentence_order}",
                    text=sentence_text,
                    page_number=page_number,
                    paragraph_id=paragraph_id,
                    order_in_paragraph=sentence_order,
                )
                sentence_units.append(sentence_unit)
                structure.sentences.append(sentence_unit)

            paragraph_unit = ParagraphUnit(
                paragraph_id=paragraph_id,
                text=paragraph_text,
                page_number=page_number,
                order_in_page=paragraph_order,
                sentences=sentence_units,
            )
            structure.paragraphs.append(paragraph_unit)

    return structure


def build_document_structure_from_chunks(file_name: str, chunkId_chunkDoc_list: list) -> DocumentStructure:
    """
    从 chunkId_chunkDoc_list 构建结构化文档
    用于接入当前项目 processing_chunks(...) 的 chunk 数据结构
    """
    temp_pages = []

    for index, item in enumerate(chunkId_chunkDoc_list, start=1):
        chunk_doc = item.get("chunk_doc")
        if chunk_doc is None:
            continue

        page_content = getattr(chunk_doc, "page_content", "") or ""
        metadata = getattr(chunk_doc, "metadata", {}) or {}

        page_number = metadata.get("page_number", index)

        temp_page = type(
            "TempPage",
            (),
            {
                "page_content": page_content,
                "metadata": {"page_number": page_number},
            },
        )()

        temp_pages.append(temp_page)

    return build_document_structure(file_name, temp_pages)