# -*- coding: utf-8 -*-
"""
三元组融合管道
将LLM提取的三元组与规则提取的三元组融合,提高提取精度
"""
import logging
from typing import List, Dict, Set, Tuple, Optional
from langchain_core.documents import Document
from langchain_neo4j.graphs.graph_document import GraphDocument, Node, Relationship
logger = logging.getLogger(__name__)

class TripletEnhancementPipeline:
    """三元组融合管道"""
    
    def __init__(self):
        self.statistics = {
            'llm_triplets': 0,
            'rule_triplets': 0,
            'merged_triplets': 0,
            'deduplicated_triplets': 0,
        }
    
    def enhance_graph_documents(self, 
                               graph_documents: List[GraphDocument],
                               source_text: str,
                               doc_type: str = 'general') -> List[GraphDocument]:
        """
        增强图文档：融合LLM提取和规则提取的三元组
        
        Args:
            graph_documents: LLM提取的图文档列表
            source_text: 源文本
            doc_type: 文档类型 ('rehabilitation', 'medical', 'general')
        
        Returns:
            增强后的图文档列表
        """
        self.statistics = {
            'llm_triplets': 0,
            'rule_triplets': 0,
            'merged_triplets': 0,
            'deduplicated_triplets': 0,
        }
        
        enhanced_docs = []
        
        for graph_doc in graph_documents:
            # 统计LLM提取的三元组
            self.statistics['llm_triplets'] += len(graph_doc.relationships)
            
            # 根据文档类型选择增强策略
            current_text = source_text
            if getattr(graph_doc, "source", None) and getattr(graph_doc.source, "page_content", None):
                current_text = graph_doc.source.page_content
            if doc_type == 'rehabilitation':
                enhanced_doc = self._enhance_rehabilitation_doc(graph_doc, current_text)
            elif doc_type == 'medical':
                enhanced_doc = self._enhance_medical_doc(graph_doc, current_text)
            else:
                enhanced_doc = self._enhance_general_doc(graph_doc, current_text)
            
            enhanced_docs.append(enhanced_doc)
        
        return enhanced_docs
    def enhance_graph_documents_with_sentence_rules(
        self,
        graph_documents: List[GraphDocument],
        file_name: str,
        chunkId_chunkDoc_list: list,
        doc_type: str = "general",
    ) -> List[GraphDocument]:
        """
        基于句子级结构和规则增强图文档
        用于把 chunk -> document_structure -> sentence labels -> rule triplets 串起来
        """
        self.statistics = {
            'llm_triplets': 0,
            'rule_triplets': 0,
            'merged_triplets': 0,
            'deduplicated_triplets': 0,
        }

        for graph_doc in graph_documents:
            self.statistics['llm_triplets'] += len(graph_doc.relationships)

        if doc_type != "rehabilitation":
            return graph_documents

        from src.document_structure_extractor import build_document_structure_from_chunks
        from src.responsibility_labeler import label_document_structure
        from src.rule_engine import extract_triplets_by_rules

        document_structure = build_document_structure_from_chunks(
            file_name=file_name,
            chunkId_chunkDoc_list=chunkId_chunkDoc_list,
        )
        document_structure = label_document_structure(document_structure)

        rule_triplets, rule_entities = extract_triplets_by_rules(document_structure)
        self.statistics['rule_triplets'] = len(rule_triplets)

        logger.info(f"句子级规则提取: {len(rule_triplets)} 个三元组")

        if not graph_documents:
            return [
                self._convert_rule_triplets_to_graph_document(
                    rule_triplets=rule_triplets,
                    rule_entities=rule_entities,
                    source_document=None,
                )
            ]

        enhanced_docs = []

        for graph_doc in graph_documents:
            sentence_rule_doc = self._convert_rule_triplets_to_graph_document(
                rule_triplets=rule_triplets,
                rule_entities=rule_entities,
                source_document=graph_doc.source,
            )

            merged_nodes = self._merge_nodes(graph_doc.nodes, sentence_rule_doc.nodes)
            merged_relationships = self._merge_relationships(
                graph_doc.relationships,
                sentence_rule_doc.relationships,
            )

            self.statistics['merged_triplets'] += len(merged_relationships)

            deduplicated_relationships = self._deduplicate_relationships(merged_relationships)
            self.statistics['deduplicated_triplets'] += len(deduplicated_relationships)

            enhanced_docs.append(
                GraphDocument(
                    nodes=merged_nodes,
                    relationships=deduplicated_relationships,
                    source=graph_doc.source,
                )
            )

        return enhanced_docs
    def _enhance_rehabilitation_doc(self, graph_doc: GraphDocument, source_text: str) -> GraphDocument:
        """增强康复训练文档"""
        from src.rehabilitation_triplet_extractor import extract_rehabilitation_triplets
        from src.rehabilitation_table_extractor import extract_table_triplets
        
        # 1. 使用规则提取器提取三元组
        rule_triplets, rule_entities = extract_rehabilitation_triplets(source_text)
        
        # 2. 使用表格提取器提取结构化数据
        table_triplets = extract_table_triplets(source_text)
        
        self.statistics['rule_triplets'] += len(rule_triplets) + len(table_triplets)
        
        logger.info(f"规则提取: {len(rule_triplets)} 个三元组")
        logger.info(f"表格提取: {len(table_triplets)} 个三元组")
        
        # 将规则提取的三元组转换为图节点和关系
        new_nodes = []
        new_relationships = []
        
        # 添加规则提取的实体作为节点
        for entity_type, entity_set in rule_entities.items():
            for entity_name in entity_set:
                node = Node(id=entity_name, type=entity_type, properties={})
                if not self._node_exists(graph_doc.nodes + new_nodes, node):
                    new_nodes.append(node)
        
        # 添加规则提取的关系
        for triplet in rule_triplets:
            source_node = Node(id=triplet.source, type=triplet.source_type, properties={})
            target_node = Node(id=triplet.target, type=triplet.target_type, properties={})
            
            # 确保节点存在
            if not self._node_exists(graph_doc.nodes + new_nodes, source_node):
                new_nodes.append(source_node)
            if not self._node_exists(graph_doc.nodes + new_nodes, target_node):
                new_nodes.append(target_node)
            
            # 创建关系
            rel = Relationship(
                source=source_node,
                target=target_node,
                type=triplet.relation,
                properties={}
            )
            
            if not self._relationship_exists(graph_doc.relationships + new_relationships, rel):
                new_relationships.append(rel)
        
        # 添加表格提取的关系
        for table_triplet in table_triplets:
            # 根据关系类型推断节点类型
            source_type = self._infer_node_type(table_triplet.source, table_triplet.relation, is_source=True)
            target_type = self._infer_node_type(table_triplet.target, table_triplet.relation, is_source=False)
            
            source_node = Node(id=table_triplet.source, type=source_type, properties={})
            target_node = Node(id=table_triplet.target, type=target_type, properties={})
            
            # 确保节点存在
            if not self._node_exists(graph_doc.nodes + new_nodes, source_node):
                new_nodes.append(source_node)
            if not self._node_exists(graph_doc.nodes + new_nodes, target_node):
                new_nodes.append(target_node)
            
            # 创建关系
            rel = Relationship(
                source=source_node,
                target=target_node,
                type=table_triplet.relation,
                properties={}
            )
            
            if not self._relationship_exists(graph_doc.relationships + new_relationships, rel):
                new_relationships.append(rel)
        
        # 合并节点和关系
        merged_nodes = self._merge_nodes(graph_doc.nodes, new_nodes)
        merged_relationships = self._merge_relationships(graph_doc.relationships, new_relationships)
        
        self.statistics['merged_triplets'] += len(merged_relationships)
        
        # 去重
        deduplicated_relationships = self._deduplicate_relationships(merged_relationships)
        self.statistics['deduplicated_triplets'] += len(deduplicated_relationships)
        
        logger.info(f"最终提取: {len(merged_nodes)} 个节点, {len(deduplicated_relationships)} 个关系")
        
        return GraphDocument(
            nodes=merged_nodes,
            relationships=deduplicated_relationships,
            source=graph_doc.source
        )
    def _convert_rule_triplets_to_graph_document(
        self,
        rule_triplets,
        rule_entities,
        source_document: Optional[Document],
    ) -> GraphDocument:
        """
        把规则提取结果转换成 GraphDocument
        """
        new_nodes = []
        new_relationships = []

        for entity_type, entity_set in rule_entities.items():
            for entity_name in entity_set:
                node = Node(id=entity_name, type=entity_type, properties={})
                if not self._node_exists(new_nodes, node):
                    new_nodes.append(node)

        for triplet in rule_triplets:
            source_node = Node(id=triplet.source, type=triplet.source_type, properties={})
            target_node = Node(id=triplet.target, type=triplet.target_type, properties={})

            if not self._node_exists(new_nodes, source_node):
                new_nodes.append(source_node)
            if not self._node_exists(new_nodes, target_node):
                new_nodes.append(target_node)

            rel = Relationship(
                source=source_node,
                target=target_node,
                type=triplet.relation,
                properties={},
            )

            if not self._relationship_exists(new_relationships, rel):
                new_relationships.append(rel)

        return GraphDocument(
            nodes=new_nodes,
            relationships=new_relationships,
            source=source_document,
        )
    def _infer_node_type(self, node_id: str, relation: str, is_source: bool) -> str:
        """根据节点ID和关系类型推断节点类型"""
        # 练习相关
        if '练习' in node_id:
            return '训练动作'
        
        # 根据关系类型推断
        if relation == '效果':
            if is_source:
                return '训练动作'
            else:
                return '效果'
        elif relation == '强化' or relation == '拉伸':
            if is_source:
                return '训练动作'
            else:
                return '解剖部位'
        elif relation == '起始姿势':
            if is_source:
                return '训练动作'
            else:
                return '姿势'
        elif relation == '动作要领':
            if is_source:
                return '训练动作'
            else:
                return '训练动作'
        elif relation == '注意事项':
            if is_source:
                return '训练动作'
            else:
                return '注意事项'
        elif relation == '重复次数':
            if is_source:
                return '训练动作'
            else:
                return '频次'
        
        # 默认类型
        return '训练动作' if is_source else '效果'
    
    def _enhance_medical_doc(self, graph_doc: GraphDocument, source_text: str) -> GraphDocument:
        """增强医学文档"""
        # 对于医学文档，主要依赖LLM提取，可以添加一些基础的规则增强
        return graph_doc
    
    def _enhance_general_doc(self, graph_doc: GraphDocument, source_text: str) -> GraphDocument:
        """增强通用文档"""
        return graph_doc
    
    def _node_exists(self, nodes: List[Node], node: Node) -> bool:
        """检查节点是否已存在"""
        return any(n.id == node.id and n.type == node.type for n in nodes)
    
    def _relationship_exists(self, relationships: List[Relationship], rel: Relationship) -> bool:
        """检查关系是否已存在"""
        return any(
            r.source.id == rel.source.id and 
            r.target.id == rel.target.id and 
            r.type == rel.type
            for r in relationships
        )
    
    def _merge_nodes(self, nodes1: List[Node], nodes2: List[Node]) -> List[Node]:
        """合并节点列表，去重"""
        merged = list(nodes1)
        for node in nodes2:
            if not self._node_exists(merged, node):
                merged.append(node)
        return merged
    
    def _merge_relationships(self, rels1: List[Relationship], rels2: List[Relationship]) -> List[Relationship]:
        """合并关系列表，去重"""
        merged = list(rels1)
        for rel in rels2:
            if not self._relationship_exists(merged, rel):
                merged.append(rel)
        return merged
    
    def _deduplicate_relationships(self, relationships: List[Relationship]) -> List[Relationship]:
        """去重关系"""
        seen = set()
        deduplicated = []
        
        for rel in relationships:
            key = (rel.source.id, rel.type, rel.target.id)
            if key not in seen:
                seen.add(key)
                deduplicated.append(rel)
        
        return deduplicated
    
    def get_statistics(self) -> Dict[str, int]:
        """获取统计信息"""
        return self.statistics.copy()


class DocumentTypeDetector:
    """文档类型检测器"""
    
    REHABILITATION_KEYWORDS = {
        '训练', '动作', '操', '运动', '锻炼', '练习', '屈伸', '旋转',
        '频次', '组', '次', '周', '天', '坐姿', '站姿', '卧姿',
        '缓解', '增强', '改善', '强化', '康复', '保健',
    }
    
    MEDICAL_KEYWORDS = {
        '疾病', '症状', '治疗', '药物', '检查', '诊断', '病因',
        '并发症', '预后', '患者', '临床', '医学', '医疗',
        '疼痛', '麻木', '头晕', '炎症', '感染', '损伤',
    }
    
    @staticmethod
    def detect_document_type(text: str) -> str:
        """
        检测文档类型
        
        Args:
            text: 文本内容
        
        Returns:
            文档类型: 'rehabilitation', 'medical', 'general'
        """
        # 统计关键词出现次数
        rehab_count = sum(text.count(kw) for kw in DocumentTypeDetector.REHABILITATION_KEYWORDS)
        medical_count = sum(text.count(kw) for kw in DocumentTypeDetector.MEDICAL_KEYWORDS)
        
        # 根据关键词出现频率判断
        if rehab_count > medical_count and rehab_count > 0:
            return 'rehabilitation'
        elif medical_count > rehab_count and medical_count > 0:
            return 'medical'
        else:
            return 'general'


if __name__ == "__main__":
    # 测试
    from src.rehabilitation_triplet_extractor import extract_rehabilitation_triplets
    
    test_text = """
    颈部屈伸训练：患者坐姿，头部缓慢向前屈曲，停留5秒，然后缓慢后伸，停留5秒。
    做3组，每组10次，每周3次。该训练可增强颈部肌肉力量，缓解颈痛。
    注意不要过度用力，避免颈部受伤。
    """
    
    # 模拟LLM提取的结果
    llm_node1 = Node(id="颈部屈伸训练", type="康复训练", properties={})
    llm_node2 = Node(id="颈痛", type="症状", properties={})
    llm_rel = Relationship(source=llm_node1, target=llm_node2, type="缓解", properties={})
    
    mock_graph_doc = GraphDocument(
        nodes=[llm_node1, llm_node2],
        relationships=[llm_rel],
        source=None
    )
    
    # 融合
    pipeline = TripletEnhancementPipeline()
    enhanced_docs = pipeline.enhance_graph_documents(
        [mock_graph_doc],
        test_text,
        doc_type='rehabilitation'
    )
    
    print("融合后的节点：")
    for node in enhanced_docs[0].nodes:
        print(f"  {node.id} ({node.type})")
    
    print("\n融合后的关系：")
    for rel in enhanced_docs[0].relationships:
        print(f"  ({rel.source.id}) -[{rel.type}]-> ({rel.target.id})")
    
    print("\n统计信息：")
    stats = pipeline.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
