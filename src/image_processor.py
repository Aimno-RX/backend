import base64
import io
import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple

import fitz
from PIL import Image

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

logging.basicConfig(format="%(asctime)s - %(message)s", level="INFO")

MAX_IMAGE_SIZE = 2048
MAX_IMAGES_PER_PAGE = 10
MIN_IMAGE_BYTES = 1024
SKIP_IMAGE_EXTENSIONS = {"x-emf", "emf", "wmf", "x-wmf"}


def _resize_image_if_needed(image_bytes: bytes, max_size: int = MAX_IMAGE_SIZE) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    width, height = img.size
    if width <= max_size and height <= max_size:
        return image_bytes

    ratio = min(max_size / width, max_size / height)
    new_size = (int(width * ratio), int(height * ratio))
    img = img.resize(new_size, Image.LANCZOS)
    buf = io.BytesIO()
    img_format = img.format or "PNG"
    img.save(buf, format=img_format)
    logging.info(f"Resized image from {width}x{height} to {new_size[0]}x{new_size[1]}")
    return buf.getvalue()


def extract_images_from_pdf(
    file_path: str, pages: Optional[List[int]] = None
) -> List[dict]:
    """
    Extract images from a PDF file.

    Args:
        file_path: Path to the PDF file.
        pages: Specific page numbers (1-indexed) to extract from. None = all pages.

    Returns:
        List of dicts: {page_number, bbox, image_bytes, extension}
    """
    images = []
    doc = fitz.open(file_path)

    target_pages = set(pages) if pages else set(range(1, doc.page_count + 1))

    for page_num in target_pages:
        if page_num < 1 or page_num > doc.page_count:
            continue
        page = doc[page_num - 1]
        image_list = page.get_images(full=True)
        logging.info(f"Page {page_num}: found {len(image_list)} image(s)")

        for img_index, img_info in enumerate(image_list):
            if len(images) >= MAX_IMAGES_PER_PAGE * doc.page_count:
                break

            xref = img_info[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            ext = base_image["ext"]

            if len(image_bytes) < MIN_IMAGE_BYTES:
                continue

            if ext.lower() in SKIP_IMAGE_EXTENSIONS:
                logging.info(f"Skipping {ext} image on page {page_num} (unsupported format)")
                continue

            try:
                image_bytes = _resize_image_if_needed(image_bytes)
            except Exception as e:
                logging.warning(f"Skipping unreadable image on page {page_num}: {e}")
                continue

            bbox = None
            for block in page.get_image_blocks():
                if block[0] == xref:
                    bbox = block[1:5]
                    break

            images.append({
                "page_number": page_num,
                "xref": xref,
                "bbox": bbox,
                "image_bytes": image_bytes,
                "extension": ext,
                "index": img_index,
            })

    doc.close()
    logging.info(f"Total images extracted: {len(images)} from {len(target_pages)} pages")
    return images


def encode_image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def extract_images_from_docx(file_path: str, max_total: int = 0) -> List[dict]:
    """
    Extract embedded images from a .docx Word document.

    Args:
        file_path: Path to the .docx file.
        max_total: Maximum total images to extract. 0 or negative means no limit.

    Returns:
        List of dicts: {paragraph_index, image_bytes, original_bytes, extension, index}
        image_bytes: resized for LLM (max 2048px)
        original_bytes: original bytes for file storage
    """
    try:
        from docx import Document
        from lxml import etree
    except ImportError as e:
        logging.warning(f"Cannot extract docx images: {e}")
        return []

    images = []
    doc = Document(file_path)

    nsmap = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
        'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
        'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
    }

    image_part_map = {}
    for rel in doc.part.rels.values():
        if "image" in rel.reltype:
            image_part_map[rel.rId] = {
                "blob": rel.target_part.blob,
                "ext": rel.target_part.content_type.split("/")[-1],
            }

    limit = max_total if max_total and max_total > 0 else float('inf')

    for para_idx, paragraph in enumerate(doc.paragraphs):
        if len(images) >= limit:
            break
        para_xml = paragraph._element
        blips = para_xml.findall('.//' + etree.QName(nsmap['a'], 'blip').text, nsmap)
        if blips is None:
            continue

        for blip in blips:
            if len(images) >= limit:
                break
            embed = blip.get(etree.QName(nsmap['r'], 'embed').text)
            if embed and embed in image_part_map:
                img_info = image_part_map[embed]
                original_bytes = img_info["blob"]
                if len(original_bytes) < MIN_IMAGE_BYTES:
                    continue
                ext = img_info["ext"].lower()
                if ext in SKIP_IMAGE_EXTENSIONS:
                    logging.info(f"Skipping EMF/WMF image at p{para_idx} (unsupported format)")
                    continue
                try:
                    resized_bytes = _resize_image_if_needed(original_bytes)
                except Exception as e:
                    logging.warning(f"Skipping unreadable image at p{para_idx}: {e}")
                    continue
                images.append({
                    "paragraph_index": para_idx,
                    "image_bytes": resized_bytes,
                    "original_bytes": original_bytes,
                    "extension": img_info["ext"],
                    "index": len(images),
                })

    logging.info(f"Extracted {len(images)} images from docx, {len(doc.paragraphs)} paragraphs")
    return images


def extract_images_from_doc(file_path: str) -> List[dict]:
    """
    Extract images from a .doc file by converting to PDF via LibreOffice first.
    Falls back gracefully if conversion fails.

    Args:
        file_path: Path to the .doc file.

    Returns:
        List of dicts: {page_number, bbox, image_bytes, extension, ...}
    """
    import subprocess
    import tempfile

    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_pdf = tmp.name

        cmd = [
            "libreoffice", "--headless", "--convert-to", "pdf",
            "--outdir", os.path.dirname(tmp_pdf),
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logging.warning(f"LibreOffice conversion failed: {result.stderr}")
            return []

        # LibreOffice names the output based on the input filename
        base = os.path.splitext(os.path.basename(file_path))[0]
        out_dir = os.path.dirname(tmp_pdf)
        converted_pdf = os.path.join(out_dir, f"{base}.pdf")
        if not os.path.exists(converted_pdf):
            logging.warning(f"Converted PDF not found at {converted_pdf}")
            return []

        images = extract_images_from_pdf(converted_pdf)

        try:
            os.unlink(converted_pdf)
        except OSError:
            pass

        return images
    except Exception as e:
        logging.warning(f"Failed to extract images from .doc: {e}")
        return []


def extract_images_from_document(
    file_path: str,
    file_extension: str,
    max_total: int = 0,
) -> Tuple[List[dict], str]:
    """
    Unified entry point: extract images from PDF, DOCX, or DOC documents.

    Args:
        file_path: Path to the document.
        file_extension: Lowercase file extension (e.g. '.pdf', '.docx', '.doc').
        max_total: Maximum images to extract. 0 or negative means no limit.

    Returns:
        Tuple of (images list, source_type).
        source_type is 'pdf_page' or 'docx_paragraph'.
    """
    ext = file_extension.lower()

    if ext == '.pdf':
        return extract_images_from_pdf(file_path), 'pdf_page'
    elif ext == '.docx':
        return extract_images_from_docx(file_path, max_total=max_total), 'docx_paragraph'
    elif ext == '.doc':
        return extract_images_from_doc(file_path), 'pdf_page'
    else:
        logging.info(f"Unsupported format for image extraction: {ext}")
        return [], 'none'


REHABILITATION_IMAGE_PROMPT = """\
This image appears in a rehabilitation / physical therapy training document on page {page_number}.

The surrounding text context from the same page is:
{page_context}

Please describe this image as a rehabilitation exercise guide. Focus on extracting:
1. **训练动作 (Exercise Name)**: What specific exercise or movement is being demonstrated?
2. **姿势 (Posture/Body Position)**: What is the starting position? Sitting, standing, lying down? What is the body's orientation?
3. **动作描述 (Movement Description)**: Describe the movement trajectory step by step. Which body parts move, in what direction, how far?
4. **训练参数 (Training Parameters)**: If visible or inferable — repetitions, sets, hold time, frequency, intensity level.
5. **针对部位 (Target Body Parts)**: Which muscles, joints, or anatomical regions are being targeted?
6. **注意事项 (Precautions)**: Any visible safety cues or warnings.

Provide the description in Chinese. Use concrete, actionable language suitable for a patient to follow."""  # noqa: E501

GENERAL_IMAGE_PROMPT = """\
This image appears on page {page_number} of a document.

The surrounding text context from the same page is:
{page_context}

Please describe this image in detail. Focus on:
1. What type of image is this (chart, diagram, table, photo, etc.)?
2. What information, data, or concepts does it convey?
3. If it's a chart or graph, describe the axes, trends, and key data points.
4. If it's a diagram, describe the structure and relationships shown.
5. If it's a table, describe the columns and key data.
Provide a concise but comprehensive description in Chinese if the context is Chinese, otherwise in English."""  # noqa: E501


def describe_image(
    vision_llm: ChatOpenAI,
    base64_image: str,
    image_format: str,
    page_context: str = "",
    page_number: int = 0,
    image_index: int = 0,
    description_mode: str = "auto",
) -> str:
    """
    Send a single image to the vision model for description.

    Args:
        vision_llm: ChatOpenAI instance configured for a vision model.
        base64_image: Base64-encoded image data.
        image_format: Image file extension (e.g. 'png', 'jpeg').
        page_context: Surrounding text from the same page for context.
        page_number: Page number where the image appears.
        image_index: Index of this image on the page.
        description_mode: 'rehabilitation', 'general', or 'auto'.
            'rehabilitation' uses exercise-focused prompt for rehab training docs.
            'general' uses a broader academic/image description prompt.
            'auto' detects from page_context whether to use rehab mode.

    Returns:
        Text description of the image content.
    """
    mime_type = f"image/{image_format}" if image_format != "jpg" else "image/jpeg"
    data_url = f"data:{mime_type};base64,{base64_image}"

    truncated_context = page_context[:3000] if page_context else ""

    if description_mode == "auto":
        rehab_signals = [
            "康复", "训练", "动作", "姿势", "拉伸", "屈伸", "颈椎", "胸椎",
            "腰椎", "物理治疗", "运动疗法", "肌力", "关节活动", "exercise",
            "rehabilitation", "physical therapy",
        ]
        context_lower = truncated_context.lower()
        is_rehab = any(s.lower() in context_lower for s in rehab_signals)
        description_mode = "rehabilitation" if is_rehab else "general"

    if description_mode == "rehabilitation":
        prompt = REHABILITATION_IMAGE_PROMPT.format(
            page_number=page_number,
            page_context=truncated_context if truncated_context else "(No surrounding text available)",
        )
    else:
        prompt = GENERAL_IMAGE_PROMPT.format(
            page_number=page_number,
            page_context=truncated_context if truncated_context else "(No surrounding text available)",
        )

    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]
    )

    try:
        response = vision_llm.invoke([message])
        description = response.content.strip()
        logging.info(
            f"Image described: page {page_number}, index {image_index}, "
            f"description length: {len(description)} chars"
        )
        return description
    except Exception as e:
        logging.error(f"Failed to describe image on page {page_number}: {e}")
        return ""


def process_document_images(
    file_path: str,
    file_extension: str,
    vision_llm: ChatOpenAI,
    pages: list = None,
    max_images: Optional[int] = None,
    description_mode: str = "auto",
) -> List[dict]:
    """
    Unified entry: extract images from any supported document, describe with
    vision model, return descriptions.
    """
    effective_max = max_images if max_images and max_images > 0 else 0
    images, source_type = extract_images_from_document(
        file_path, file_extension, max_total=effective_max
    )

    if not images:
        return []

    page_text_map = {}
    if pages:
        for i, p in enumerate(pages):
            pn = p.metadata.get("page_number", i + 1)
            page_text_map[pn] = p.page_content

    results = []
    for img in images:
        try:
            if source_type == "pdf_page":
                page_num = img.get("page_number", 0)
                context = page_text_map.get(page_num, "")
            else:
                para_idx = img.get("paragraph_index", 0)
                context = _get_paragraph_context(pages, para_idx) if pages else ""

            b64 = encode_image_to_base64(img["image_bytes"])

            ext = img.get("extension", "png").lower()
            if ext in SKIP_IMAGE_EXTENSIONS:
                continue

            description = describe_image(
                vision_llm=vision_llm,
                base64_image=b64,
                image_format=ext,
                page_context=context,
                page_number=img.get("page_number", img.get("paragraph_index", 0)),
                image_index=img["index"],
                description_mode=description_mode,
            )

            if description:
                entry = {
                    "description": description,
                    "image_index": img["index"],
                }
                if source_type == "pdf_page":
                    entry["page_number"] = img.get("page_number", 0)
                else:
                    entry["paragraph_index"] = img.get("paragraph_index", 0)
                results.append(entry)
        except Exception as e:
            logging.warning(f"Failed to process image {img.get('index', '?')}: {e}")
            continue

    logging.info(f"Described {len(results)}/{len(images)} images from {file_extension}")
    return results


def _get_paragraph_context(pages: list, para_index: int, window: int = 2) -> str:
    paragraphs = []
    for page in pages:
        paragraphs.extend(page.page_content.split("\n\n"))

    start = max(0, para_index - window)
    end = min(len(paragraphs), para_index + window + 1)
    return "\n".join(paragraphs[start:end])


def process_pdf_images(
    file_path: str,
    vision_llm: ChatOpenAI,
    pages_text: Optional[List[Tuple[int, str]]] = None,
    max_images: Optional[int] = None,
    description_mode: str = "auto",
) -> List[dict]:
    """
    Extract images from PDF, describe with vision model, return descriptions.
    Legacy wrapper, use process_document_images instead.
    """
    if not file_path.lower().endswith(".pdf"):
        logging.info("Not a PDF file, skipping image extraction")
        return []

    if not os.path.exists(file_path):
        logging.warning(f"File not found for image extraction: {file_path}")
        return []

    images = extract_images_from_pdf(file_path)

    if max_images and len(images) > max_images:
        logging.info(f"Limiting images from {len(images)} to {max_images}")
        images = images[:max_images]

    page_text_map = {}
    if pages_text:
        for pn, text in pages_text:
            page_text_map[pn] = text

    results = []
    for img in images:
        page_num = img["page_number"]
        page_context = page_text_map.get(page_num, "")
        b64 = encode_image_to_base64(img["image_bytes"])

        description = describe_image(
            vision_llm=vision_llm,
            base64_image=b64,
            image_format=img["extension"],
            page_context=page_context,
            page_number=page_num,
            image_index=img["index"],
            description_mode=description_mode,
        )

        if description:
            results.append({
                "page_number": page_num,
                "description": description,
                "image_index": img["index"],
            })

    logging.info(f"Successfully described {len(results)}/{len(images)} images")
    return results


def merge_image_descriptions_into_pages(
    pages: list,
    image_descriptions: List[dict],
) -> list:
    """
    Merge image descriptions into the corresponding page Documents.

    Supports both PDF-style (page_number) and DOCX-style (paragraph_index)
    image descriptions.

    Args:
        pages: List of langchain Document objects (must have page_number metadata).
        image_descriptions: List from process_document_images or process_pdf_images.

    Returns:
        Modified list of Document objects with image descriptions appended.
    """
    from langchain_core.documents import Document

    has_page_numbers = any("page_number" in d for d in image_descriptions)
    has_para_indices = any("paragraph_index" in d for d in image_descriptions)

    if has_page_numbers:
        page_desc_map = {}
        for desc in image_descriptions:
            pn = desc.get("page_number", 0)
            if pn not in page_desc_map:
                page_desc_map[pn] = []
            page_desc_map[pn].append(desc["description"])

        for i, page in enumerate(pages):
            page_num = page.metadata.get("page_number", i + 1)
            if page_num in page_desc_map:
                desc_text = "\n\n".join(
                    f"[Figure {j+1} Description]: {d}"
                    for j, d in enumerate(page_desc_map[page_num])
                )
                pages[i] = Document(
                    page_content=page.page_content + "\n\n" + desc_text,
                    metadata=page.metadata,
                )

    elif has_para_indices and image_descriptions:
        all_descriptions = []
        for desc in sorted(image_descriptions, key=lambda d: d.get("paragraph_index", 0)):
            all_descriptions.append(
                f"[Document Figure {desc.get('image_index', 0) + 1} Description]: {desc['description']}"
            )
        combined = "\n\n".join(all_descriptions)
        if pages:
            pages[0] = Document(
                page_content=pages[0].page_content + "\n\n" + combined,
                metadata=pages[0].metadata,
            )

    return pages
