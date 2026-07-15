import logging
import os
from pathlib import Path
import chardet
from langchain_community.document_loaders import PyMuPDFLoader, UnstructuredFileLoader
from langchain_core.documents import Document
from langchain_core.document_loaders import BaseLoader

# 配置常量
MAX_FILE_SIZE_MB = 2048  # 2GB 限制
MAX_IMAGE_SIZE_MB = 100  # 单个图片最大100MB

class ListLoader(BaseLoader):
    """
    A wrapper to make a list of Documents compatible with BaseLoader.
    """
    def __init__(self, documents):
        self.documents = documents

    def load(self):
        """
        Returns the list of documents.
        """
        return self.documents

def check_file_size(file_path):
    """
    检查文件大小是否在允许范围内
    
    Args:
        file_path (str or Path): 文件路径
        
    Returns:
        tuple: (is_valid, size_mb, message)
    """
    file_size = os.path.getsize(file_path)
    size_mb = file_size / (1024 * 1024)
    
    if size_mb > MAX_FILE_SIZE_MB:
        return False, size_mb, f"文件大小 {size_mb:.2f}MB 超过限制 {MAX_FILE_SIZE_MB}MB"
    
    return True, size_mb, f"文件大小: {size_mb:.2f}MB"

def detect_encoding(file_path):
    """
    Detects the file encoding to avoid UnicodeDecodeError.

    Args:
        file_path (str or Path): Path to the file.

    Returns:
        str: Detected encoding (default "utf-8" if not found).
    """
    with open(file_path, 'rb') as f:
        raw_data = f.read(4096)
        result = chardet.detect(raw_data)
        return result['encoding'] or "utf-8"

def load_document_content(file_path):
    """
    优化的文档加载，专门处理包含大量图片的文档
    
    Args:
        file_path (str or Path): Path to the file.

    Returns:
        tuple: (loader, encoding_flag)
            loader: Document loader instance.
            encoding_flag (bool): True if non-UTF-8 encoding was used for .txt files.
    """
    file_extension = Path(file_path).suffix.lower()
    encoding_flag = False
    
    # 检查文件大小
    is_valid, size_mb, message = check_file_size(file_path)
    logging.info(message)
    
    if not is_valid:
        raise Exception(message)
    
    # PDF 文件处理
    if file_extension == '.pdf':
        loader = PyMuPDFLoader(file_path)
        return loader, encoding_flag
    
    # TXT 文件处理
    if file_extension == ".txt":
        encoding = detect_encoding(file_path)
        logging.info("Detected encoding for text file: %s", encoding)
        if encoding.lower() == "utf-8":
            loader = UnstructuredFileLoader(file_path, mode="elements", autodetect_encoding=True)
            return loader, encoding_flag
        with open(file_path, encoding=encoding, errors="replace") as f:
            content = f.read()
        loader = ListLoader([Document(page_content=content, metadata={"source": file_path})])
        encoding_flag = True
        return loader, encoding_flag
    
    # DOCX 等文档处理 - 针对大文件和包含图片的文档优化
    if file_extension in ['.docx', '.doc']:
        # 对于大于10MB的文档，使用快速策略跳过图片处理
        if size_mb > 10:
            logging.info(f"大文件检测 ({size_mb:.2f}MB)，使用快速文本提取策略（跳过图片）")
            try:
                # 使用 fast 策略，跳过图片和复杂格式
                loader = UnstructuredFileLoader(
                    file_path, 
                    mode="elements",
                    strategy="fast",  # 快速策略，只提取文本
                    autodetect_encoding=True
                )
                return loader, encoding_flag
            except Exception as e:
                logging.warning(f"快速策略失败，尝试基础策略: {e}")
                # 如果快速策略失败，使用最基础的策略
                loader = UnstructuredFileLoader(
                    file_path,
                    mode="elements",
                    autodetect_encoding=True
                )
                return loader, encoding_flag
        else:
            # 小文件使用标准策略
            loader = UnstructuredFileLoader(
                file_path,
                mode="elements",
                autodetect_encoding=True
            )
            return loader, encoding_flag
    
    # 其他文件类型
    loader = UnstructuredFileLoader(file_path, mode="elements", autodetect_encoding=True)
    return loader, encoding_flag

def get_documents_from_file_by_path(file_path, file_name):
    """
    优化版本：从文件路径加载文档，支持大文件和图片处理

    Args:
        file_path (str or Path): Path to the file.
        file_name (str): Name of the file.

    Returns:
        tuple: (file_name, pages, file_extension)

    Raises:
        Exception: If file does not exist or reading fails.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        logging.info('File %s does not exist', file_name)
        raise Exception(f'File {file_name} does not exist')
    
    logging.info('Processing file: %s', file_name)
    
    try:
        loader, encoding_flag = load_document_content(file_path)
        file_extension = file_path.suffix.lower()
        
        if file_extension == ".pdf" or (file_extension == ".txt" and encoding_flag):
            pages = loader.load()
        else:
            unstructured_pages = loader.load()
            
            # 过滤掉图片元素，只保留文本
            text_pages = []
            for page in unstructured_pages:
                # 跳过图片类型的元素
                if page.metadata.get('category') not in ['Image', 'Figure']:
                    text_pages.append(page)
            
            logging.info(f"原始元素数: {len(unstructured_pages)}, 文本元素数: {len(text_pages)}")
            
            pages = get_pages_with_page_numbers(text_pages)
        
        logging.info(f"成功处理文件 {file_name}，共 {len(pages)} 页")
        
    except Exception as exc:
        error_msg = f'处理文件时出错: {exc}'
        logging.error(error_msg)
        raise Exception(error_msg)
    
    return file_name, pages, file_extension

def get_pages_with_page_numbers(unstructured_pages):
    """
    Groups unstructured pages into logical pages with page numbers and metadata.
    """
    if not unstructured_pages:
        return []

    grouped_pages = {}

    for page in unstructured_pages:
        metadata = page.metadata or {}
        if metadata.get('category') == 'PageBreak':
            continue

        current_page_number = metadata.get('page_number', 1)
        if current_page_number not in grouped_pages:
            grouped_pages[current_page_number] = {
                'content': [],
                'metadata': {
                    'source': metadata.get('source'),
                    'page_number': current_page_number,
                    'filename': metadata.get('filename'),
                    'filetype': metadata.get('filetype')
                }
            }

        text = (page.page_content or '').strip()
        if text:
            grouped_pages[current_page_number]['content'].append(text)

    pages = []
    for current_page_number in sorted(grouped_pages.keys()):
        page_info = grouped_pages[current_page_number]
        page_content = "\n".join(page_info['content']).strip()
        if page_content:
            pages.append(Document(page_content=page_content, metadata=page_info['metadata']))

    return pages
