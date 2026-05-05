"""
自定义Neo4j检索器包装器 - 直接执行Cypher查询传递query_vector参数
"""
import logging
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain_neo4j import Neo4jVector

logger = logging.getLogger(__name__)

class CustomNeo4jRetriever(BaseRetriever):
    neo4j_vector: Neo4jVector = None
    embedding_function: Embeddings = None
    search_type: str = "similarity_score_threshold"
    search_kwargs: Dict[str, Any] = {}
    
    def __init__(
        self,
        neo4j_vector: Neo4jVector,
        embedding_function: Embeddings,
        search_type: str = "similarity_score_threshold",
        search_kwargs: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.neo4j_vector = neo4j_vector
        self.embedding_function = embedding_function
        self.search_type = search_type
        self.search_kwargs = search_kwargs or {}
        logger.info(f"CustomNeo4jRetriever初始化")
    
    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        try:
            query_vector = self.embedding_function.embed_query(query)
            logger.info(f"查询向量维度: {len(query_vector)}")
            
            top_k = self.search_kwargs.get('top_k', 5)
            filter_dict = self.search_kwargs.get('filter')
            
            # 获取retrieval_query
            retrieval_query = getattr(self.neo4j_vector, 'retrieval_query', None)
            index_name = getattr(self.neo4j_vector, 'index_name', 'vector')
            
            # 构建基础向量检索查询
            base_query = f"""
            CALL db.index.vector.queryNodes('{index_name}', toInteger($top_k),$query_vector)
            YIELD node, score
            """
            
            # 如果有retrieval_query，使用它；否则使用简单查询
            if retrieval_query:
                # 替换retrieval_query中的node变量
                full_query = base_query + "\nWITH node, score\n" + retrieval_query
            else:
                full_query = base_query + """
                OPTIONAL MATCH (node)-[:PART_OF]->(d:Document)
                RETURN node.text AS text, score, 
                       {source: COALESCE(d.fileName, 'unknown')} AS metadata
                """
            
            # 构建参数
            params = {
                'query_vector': query_vector,
                'top_k': top_k
            }
            
            if filter_dict:
                params['filter'] = filter_dict
            
            # 执行查询
            logger.info(f"执行向量检索查询，index={index_name}, top_k={top_k}")
            results = self.neo4j_vector.query(full_query, params=params)
            
            # 转换为Document对象
            docs = []
            for result in results:
                text = result.get('text', '')
                metadata = dict(result.get('metadata', {}))
                score = result.get('score', 0)
                docs.append(Document(page_content=text, metadata=metadata))
            
            logger.info(f"检索到 {len(docs)} 个文档")
            return docs
            
        except Exception as e:
            logger.error(f"检索失败: {e}", exc_info=True)
            raise
    
    async def _aget_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        return self._get_relevant_documents(query, run_manager=run_manager)


def create_custom_retriever(
    neo4j_vector: Neo4jVector,
    embedding_function: Embeddings,
    document_names: Optional[List[str]] = None,
    search_k: int = 5,
    score_threshold: float = 0.5,
    ef_ratio: float = 1.0,
    search_type: str = "similarity_score_threshold"
) -> CustomNeo4jRetriever:
    search_kwargs = {
        'top_k': search_k,
        'effective_search_ratio': ef_ratio,
        'score_threshold': score_threshold
    }
    
    if document_names:
        search_kwargs['filter'] = {'fileName': {'$in': document_names}}
    
    return CustomNeo4jRetriever(
        neo4j_vector=neo4j_vector,
        embedding_function=embedding_function,
        search_type=search_type,
        search_kwargs=search_kwargs
    )
