"""
自定义图谱抽取器 - 兼容DeepSeek等不同LLM的输出格式
解决: 'list' object has no attribute 'get' 错误
"""
import logging
import json
import re
from typing import List, Optional, Any
from langchain_core.documents import Document
from langchain_community.graphs.graph_document import GraphDocument, Node, Relationship


def normalize_triple_format(llm_output: Any) -> List[dict]:
    """
    标准化不同LLM的三元组输出格式
    
    支持格式:
    1. 标准格式: [{"head": "节点1", "tail": "节点2", "relation": "关系"}, ...]
    2. 列表格式: [["节点1", "节点2", "关系"], ...]
    3. 混合格式: 上述两种混合
    
    Returns:
        标准化后的dict列表
    """
    if not llm_output:
        return []
    
    # 如果是字符串，尝试解析JSON
    if isinstance(llm_output, str):
        try:
            llm_output = json.loads(llm_output)
        except:
            # 尝试修复常见JSON格式问题
            llm_output = fix_json_format(llm_output)
            try:
                llm_output = json.loads(llm_output)
            except:
                logging.error(f"无法解析LLM输出: {llm_output[:200]}")
                return []
    
    # 如果不是列表，包装成列表
    if not isinstance(llm_output, list):
        llm_output = [llm_output]
    
    normalized = []
    for item in llm_output:
        try:
            # 格式1: 列表格式 ["节点1", "节点2", "关系"]
            if isinstance(item, list):
                if len(item) >= 3:
                    triple = {
                        "head": str(item[0]).strip(),
                        "tail": str(item[1]).strip(),
                        "relation": str(item[2]).strip(),
                        "head_type": str(item[3]).strip() if len(item) > 3 else "Entity",
                        "tail_type": str(item[4]).strip() if len(item) > 4 else "Entity"
                    }
                    normalized.append(triple)
                else:
                    logging.warning(f"跳过无效三元组(长度不足): {item}")
            
            # 格式2: 字典格式 {"head": "节点1", "tail": "节点2", "relation": "关系"}
            elif isinstance(item, dict):
                # 检查必要字段
                if "head" in item and "tail" in item and "relation" in item:
                    normalized.append(item)
                # 可能使用了不同的键名
                elif len(item) >= 3:
                    # 尝试从字典中提取
                    keys = list(item.keys())
                    triple = {
                        "head": str(item.get(keys[0], "")).strip(),
                        "tail": str(item.get(keys[1], "")).strip(),
                        "relation": str(item.get(keys[2], "")).strip(),
                    }
                    if len(keys) > 3:
                        triple["head_type"] = str(item.get(keys[3], "Entity")).strip()
                    if len(keys) > 4:
                        triple["tail_type"] = str(item.get(keys[4], "Entity")).strip()
                    normalized.append(triple)
                else:
                    logging.warning(f"跳过无效三元组(dict): {item}")
            
            else:
                logging.warning(f"跳过不支持的三元组格式: {type(item)} - {item}")
        
        except Exception as e:
            logging.error(f"标准化三元组失败: {e}, item: {item}")
            continue
    
    logging.info(f"三元组标准化完成: {len(normalized)} 个有效三元组")
    return normalized


def fix_json_format(json_str: str) -> str:
    """
    修复常见的JSON格式问题
    """
    # 移除可能的前缀文字
    json_str = re.sub(r'^.*?($$|\{)', r'\1', json_str, flags=re.DOTALL)
    
    # 移除可能的后缀文字
    json_str = re.sub(r'($$|\}).*?$', r'\1', json_str, flags=re.DOTALL)
    
    # 修复单引号为双引号
    json_str = json_str.replace("'", '"')
    
    # 修复缺少引号的键
    json_str = re.sub(r'(\{|,)\s*(\w+)\s*:', r'\1"\2":', json_str)
    
    return json_str


def create_graph_documents_from_triples(
    triples: List[dict],
    source_document: Document,
    allowed_nodes: Optional[List[str]] = None,
    allowed_relationships: Optional[List[tuple]] = None
) -> GraphDocument:
    """
    从标准化的三元组创建GraphDocument
    
    Args:
        triples: 标准化的三元组列表
        source_document: 源文档
        allowed_nodes: 允许的节点类型
        allowed_relationships: 允许的关系类型
    
    Returns:
        GraphDocument对象
    """
    nodes_set = set()
    relationships = []
    
    DEFAULT_NODE_TYPE = "Entity"
    
    for triple in triples:
        try:
            head = triple.get("head", "").strip()
            tail = triple.get("tail", "").strip()
            relation = triple.get("relation", "").strip()
            
            # 跳过空值
            if not head or not tail or not relation:
                continue
            
            # 获取节点类型
            head_type = triple.get("head_type", DEFAULT_NODE_TYPE).strip()
            tail_type = triple.get("tail_type", DEFAULT_NODE_TYPE).strip()
            
            # 检查是否在允许列表中
            if allowed_nodes:
                if head_type not in allowed_nodes:
                    head_type = DEFAULT_NODE_TYPE
                if tail_type not in allowed_nodes:
                    tail_type = DEFAULT_NODE_TYPE
            
            if allowed_relationships:
                # 检查关系是否在允许列表中
                relation_allowed = False
                for src_type, rel_type, tgt_type in allowed_relationships:
                    if relation == rel_type:
                        relation_allowed = True
                        break
                if not relation_allowed:
                    continue
            
            # 创建节点（去重）
            node1_key = (head, head_type)
            node2_key = (tail, tail_type)
            
            nodes_set.add(node1_key)
            nodes_set.add(node2_key)
            
            # 创建关系
            source_node = Node(id=head, type=head_type)
            target_node = Node(id=tail, type=tail_type)
            
            rel = Relationship(
                source=source_node,
                target=target_node,
                type=relation
            )
            relationships.append(rel)
        
        except Exception as e:
            logging.error(f"创建关系失败: {e}, triple: {triple}")
            continue
    
    # 创建节点列表
    nodes = [Node(id=node_id, type=node_type) for node_id, node_type in nodes_set]
    
    # 创建GraphDocument
    graph_doc = GraphDocument(
        nodes=nodes,
        relationships=relationships,
        source=source_document
    )
    
    return graph_doc


class DeepSeekCompatibleGraphTransformer:
    """
    DeepSeek兼容的图谱转换器
    包装LLMGraphTransformer，处理DeepSeek的特殊返回格式
    """
    
    def __init__(self, base_transformer, llm=None, allowed_nodes=None, allowed_relationships=None):
        self.base_transformer = base_transformer
        self.llm = llm
        self.allowed_nodes = allowed_nodes
        self.allowed_relationships = allowed_relationships
    
    async def aconvert_to_graph_documents(
        self,
        documents: List[Document]
    ) -> List[GraphDocument]:
        """
        异步转换文档为图谱，带格式兼容处理
        """
        try:
            # 尝试使用基础转换器
            graph_docs = await self.base_transformer.aconvert_to_graph_documents(documents)
            return graph_docs
        
        except AttributeError as e:
            # 捕获 'list' object has no attribute 'get' 错误
            if "'list' object has no attribute 'get'" in str(e) or "get" in str(e):
                logging.warning(f"检测到DeepSeek格式问题，启动兼容模式: {e}")
                return await self._convert_with_compatibility(documents)
            else:
                raise
        
        except Exception as e:
            logging.error(f"图谱转换失败: {e}")
            raise
    
    async def _convert_with_compatibility(
        self,
        documents: List[Document]
    ) -> List[GraphDocument]:
        """
        兼容模式：手动调用LLM并处理输出
        """
        graph_documents = []
        
        for doc in documents:
            try:
                if not self.llm:
                    logging.error("兼容模式需要llm实例，但未提供")
                    continue
                
                prompt = self._build_extraction_prompt(doc.page_content)
                response = await self.llm.ainvoke(prompt)
                
                # 提取内容
                content = response.content if hasattr(response, 'content') else str(response)
                
                # 标准化三元组
                triples = normalize_triple_format(content)
                
                if triples:
                    # 创建GraphDocument
                    graph_doc = create_graph_documents_from_triples(
                        triples,
                        doc,
                        self.allowed_nodes,
                        self.allowed_relationships
                    )
                    graph_documents.append(graph_doc)
                    logging.info(f"兼容模式成功提取: {len(triples)} 个三元组")
            
            except Exception as e:
                logging.error(f"兼容模式处理文档失败: {e}")
                continue
        
        return graph_documents
    
    def _build_extraction_prompt(self, text: str) -> str:
        """
        构建实体抽取提示词
        """
        return f"""从以下文本中提取实体和关系三元组。

输出格式要求（JSON数组）:
[
  {{"head": "实体1", "tail": "实体2", "relation": "关系", "head_type": "类型", "tail_type": "类型"}},
  ...
]

文本内容:
{text}

请输出JSON格式的三元组数组:"""