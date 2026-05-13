import logging
import re
from langchain_core.documents import Document
from langchain_neo4j import Neo4jGraph
from langchain_text_splitters import TokenTextSplitter

# from src.document_sources.youtube import  # 注释：不使用YouTube功能 get_calculated_timestamps, get_chunks_with_timestamps
from src.shared.common_fn import get_value_from_env
from src.medical_extraction_config import BATCH_PROCESSING_CONFIG

logging.basicConfig(format="%(asctime)s - %(message)s", level="INFO")


class CreateChunksofDocument:
    """
    Class to handle splitting a list of documents (pages) into smaller chunks.
    """

    def __init__(self, pages: list[Document], graph: Neo4jGraph):
        """
        Initialize the chunk creator.

        Args:
            pages (list[Document]): List of langchain Document objects representing pages.
            graph (Neo4jGraph): Neo4j graph connection object.
        """
        self.pages = pages
        self.graph = graph

    def split_file_into_chunks(self, token_chunk_size: int, chunk_overlap: int, email: str):
        """
        Split a list of documents (pages) into chunks of fixed token size.
        优化：使用医学文本优化的分块策略，并预过滤无效内容

        Args:
            token_chunk_size (int): Number of tokens per chunk.
            chunk_overlap (int): Number of tokens to overlap between chunks.
            email (str): User email for chunk limiting logic.

        Returns:
            list[Document]: List of langchain Document chunks.
        """
        logging.info("Split file into smaller chunks with medical optimization")
        optimized_chunk_size = BATCH_PROCESSING_CONFIG.get("max_chunk_size", token_chunk_size or 512)
        optimized_overlap = BATCH_PROCESSING_CONFIG.get("chunk_overlap", chunk_overlap or 80)

        # 优先使用外部传入的动态参数；只有未传值时才回退到医学默认配置
        token_chunk_size = token_chunk_size or optimized_chunk_size
        chunk_overlap = chunk_overlap or optimized_overlap

        if token_chunk_size <= 0:
            token_chunk_size = optimized_chunk_size

        if chunk_overlap < 0:
            chunk_overlap = 0
        if chunk_overlap >= token_chunk_size:
            adjusted_overlap = max(0, token_chunk_size // 5)
            logging.info(
                f"chunk_overlap ({chunk_overlap}) >= token_chunk_size ({token_chunk_size})，自动调整为 {adjusted_overlap}"
            )
            chunk_overlap = adjusted_overlap

        text_splitter = TokenTextSplitter(chunk_size=token_chunk_size, chunk_overlap=chunk_overlap)
        max_token_chunk_size = get_value_from_env("MAX_TOKEN_CHUNK_SIZE", 1000000, "int")
        chunk_to_be_created = max(1, int(max_token_chunk_size / max(token_chunk_size, 1)))
        normalized_email = (email or "").strip().lower() or None
        is_neo4j_user = bool(normalized_email and normalized_email.endswith("@neo4j.com"))

        chunks = []
        first_metadata = self.pages[0].metadata

        if 'page' in first_metadata:
            # PDF or paginated document
            for i, document in enumerate(self.pages):
                page_number = i + 1
                for chunk in text_splitter.split_documents([document]):
                    chunks.append(Document(page_content=chunk.page_content, metadata={'page_number': page_number}))
        elif 'length' in first_metadata:
            # YouTube transcript or similar
            if len(self.pages) == 1 or (len(self.pages) > 1 and self.pages[1].page_content.strip() == ''):
                match = re.search(r'(?:v=)([0-9A-Za-z_-]{11})\s*', self.pages[0].metadata.get('source', ''))
                youtube_id = match.group(1) if match else None
                chunks_without_time_range = text_splitter.split_documents([self.pages[0]])
                if youtube_id:
                    chunks = get_calculated_timestamps(chunks_without_time_range, youtube_id)
                else:
                    chunks = chunks_without_time_range
            else:
                chunks_without_time_range = text_splitter.split_documents(self.pages)
                chunks = get_chunks_with_timestamps(chunks_without_time_range)
        else:
            logging.info("No metadata found for pages, proceeding with normal chunking")
            chunks = text_splitter.split_documents(self.pages)

        logging.info('Total chunks created: %d', len(chunks))
        
        # ================== 新增：预过滤无效chunk ==================
        from src.medical_extraction_config import filter_empty_chunks
        original_chunk_count = len(chunks)
        chunks = filter_empty_chunks(chunks)
        filtered_chunk_count = len(chunks)
        
        if filtered_chunk_count < original_chunk_count:
            logging.info(f'预过滤无效chunk: {original_chunk_count} -> {filtered_chunk_count} (减少 {original_chunk_count - filtered_chunk_count} 个)')
        # ================== 过滤结束 ==================
        
        if not is_neo4j_user and len(chunks) > chunk_to_be_created:
            original_chunk_count = len(chunks)
            chunks = chunks[:chunk_to_be_created]
            logging.info('Limiting chunks to %d from %d based on MAX_TOKEN_CHUNK_SIZE', chunk_to_be_created, original_chunk_count)
        return chunks