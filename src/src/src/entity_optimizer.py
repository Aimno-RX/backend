# -*- coding: utf-8 -*-
"""
实体优化模块
用于后处理提取的实体，提高知识图谱质量
"""

import logging
import re
from typing import List, Dict, Any, Set
from collections import defaultdict

logging.basicConfig(format='%(asctime)s - %(message)s', level='INFO')


class EntityOptimizer:
    """
    实体优化器
    负责清理、合并和优化提取的实体
    """
    
    def __init__(self):
        """初始化实体优化器"""
        # 无效实体模式（需要过滤的）
        self.invalid_patterns = [
            r'^第[一二三四五六七八九十\d]+章',
            r'^第[一二三四五六七八九十\d]+节',
            r'^\d+\s*$',
            r'^目录$',
            r'^参考文献$',
            r'^作者$',
            r'^出版社$',
            r'^[一二三四五六七八九十]+、',
            r'^\s*$',
        ]
        
        # 过于宽泛的词汇（需要过滤）
        # 注意：只过滤真正无意义的通用词，不要过滤医学专业词汇
        self.generic_terms = {
            '方法', '问题', '情况', '方式', '过程', '结果',
            '意义', '目的', '内容', '特点', '性质', '形式',
            '阶段', '时期', '部分', '方面', '条件', '环境'
            # 注意：'原因'、'因素'、'影响'、'效果'、'状态'、'程度'、'范围'、'类型'、'关系'
            # 这些词在医学语境下可能是有效实体的一部分，不再过滤
        }
        
        # 实体同义词映射（用于合并）
        # 注意：只合并完全等价的同义词，不要跨语言合并（如中文->英文）
        self.synonym_map = {
            '颈椎间盘突出症': '颈椎间盘突出',  # 全称->简称
            '颈椎退行性变': '颈椎退变',
            '颈椎间盘退行性变': '颈椎间盘退变',
        }

        self.type_mapping = {
            "Disease": "疾病",
            "Symptom": "症状",
            "Sign": "体征",
            "Anatomy": "解剖部位",
            "Treatment": "治疗方法",
            "Drug": "药物",
            "Medication": "药物",
            "Examination": "检查项目",
            "Cause": "病因",
            "Complication": "并发症",
            "Risk_Factor": "危险因素",
            "Prevention": "预防",
            "Prognosis": "预后",
            "Rehabilitation": "康复训练",
            "Surgery": "手术",
            "Pathology": "病理变化",
            "PainType": "疼痛类型",
            "PainMechanism": "疼痛机制",
            "Exercise": "训练动作",
            "Posture": "姿势",
            "Frequency": "频次",
            "Effect": "效果",
            "Precaution": "注意事项",
            "MuscleGroup": "肌肉群",
            "AssessmentTool": "评估方法",
            "PsychologicalFactor": "心理因素",
            "SocialFactor": "社会因素",
            "PrognosticFactor": "预后因素",
            "Biomarker": "生物标志物",
            "Neurotransmitter": "神经递质",
            "NeuralFiber": "神经纤维",
            "NervousSystem": "神经通路",
            "OccupationGroup": "职业人群",
            "Acupoint": "穴位",
            "Equipment": "设备",
            "ClinicalFeature": "临床表现",
        }

        self.relationship_mapping = {
            "HAS_SYMPTOM": "有症状",
            "AFFECTS": "影响部位",
            "CAUSED_BY": "病因是",
            "TREATED_BY": "治疗方法",
            "REQUIRES": "需要检查",
            "HAS_RISK_FACTOR": "危险因素",
            "LEADS_TO": "导致",
            "PREVENTED_BY": "预防",
            "HAS_MECHANISM": "涉及疼痛机制",
            "INVOLVES": "涉及",
            "RELEASES": "释放",
            "INDICATES": "指示",
            "MODULATES": "影响",
            "ASSOCIATED_WITH": "关联",
            "PREDICTS": "预后因素",
            "MEASURED_BY": "测量",
            "USES": "用药",
            "TARGETS": "作用部位",
            "IMPROVES": "缓解",
            "HAS_STEP": "包含",
            "STRENGTHENS": "强化",
            "STRETCHES": "拉伸",
            "HAS_STARTING_POSTURE": "起始姿势",
            "HAS_FREQUENCY": "频次",
            "HAS_PRECAUTION": "注意事项",
            "ACHIEVES": "效果",
            "LOCATED_IN": "位于",
            "PART_OF": "属于",
            "PREVENTS": "预防",
            "DIAGNOSES": "诊断",
            "TREATS": "治疗",
            "RELIEVES": "缓解",
            "ADJACENT_TO": "邻近",
            "EXAMINES": "检查部位",
        }
    
    def is_valid_entity(self, entity_name: str, entity_type: str = None) -> bool:
        """
        检查实体是否有效
        
        Args:
            entity_name: 实体名称
            entity_type: 实体类型
            
        Returns:
            bool: 是否有效
        """
        if not entity_name or not isinstance(entity_name, str):
            return False
        
        entity_name = entity_name.strip()
        
        # 检查长度
        if len(entity_name) < 2 or len(entity_name) > 50:
            return False
        
        # 检查是否匹配无效模式
        for pattern in self.invalid_patterns:
            if re.match(pattern, entity_name):
                return False
        
        # 检查是否为过于宽泛的词汇
        if entity_name in self.generic_terms:
            return False
        
        # 检查是否只包含标点符号
        if re.match(r'^[^\w\u4e00-\u9fff]+$', entity_name):
            return False
        
        return True
    
    def normalize_entity_name(self, entity_name: str) -> str:
        """
        标准化实体名称
        
        Args:
            entity_name: 原始实体名称
            
        Returns:
            标准化后的实体名称
        """
        if not entity_name:
            return entity_name
        
        # 去除首尾空白
        entity_name = entity_name.strip()
        
        # 去除多余的空格
        entity_name = re.sub(r'\s+', ' ', entity_name)
        
        # 去除特殊字符
        entity_name = re.sub(r'["""\'\'`]', '', entity_name)
        
        # 应用同义词映射
        if entity_name in self.synonym_map:
            entity_name = self.synonym_map[entity_name]
        
        return entity_name
    
    def filter_graph_documents(self, graph_documents: List[Any]) -> List[Any]:
        """
        过滤图文档，移除无效实体和关系
        
        Args:
            graph_documents: 图文档列表
            
        Returns:
            过滤后的图文档列表
        """
        filtered_docs = []
        total_nodes_before = 0
        total_nodes_after = 0
        total_rels_before = 0
        total_rels_after = 0
        
        for doc in graph_documents:
            total_nodes_before += len(doc.nodes) if doc.nodes else 0
            total_rels_before += len(doc.relationships) if doc.relationships else 0
            
            # 过滤节点
            if doc.nodes:
                valid_nodes = []
                valid_node_ids = set()
                
                for node in doc.nodes:
                    node_id = getattr(node, 'id', None)
                    node_type = getattr(node, 'type', None)

                    if node_type in self.type_mapping:
                        node.type = self.type_mapping[node_type]

                    if self.is_valid_entity(node_id, node.type):
                        normalized_id = self.normalize_entity_name(node_id)
                        node.id = normalized_id
                        valid_nodes.append(node)
                
                doc.nodes = valid_nodes
            
            # 过滤关系（只保留两端节点都有效的关系）
            if doc.relationships:
                valid_relationships = []
                
                for rel in doc.relationships:
                    if getattr(rel, 'type', None) in self.relationship_mapping:
                        rel.type = self.relationship_mapping[rel.type]
                    if hasattr(rel, 'source') and getattr(rel.source, 'type', None) in self.type_mapping:
                        rel.source.type = self.type_mapping[rel.source.type]
                    if hasattr(rel, 'target') and getattr(rel.target, 'type', None) in self.type_mapping:
                        rel.target.type = self.type_mapping[rel.target.type]
                    source_id = getattr(rel.source, 'id', None) if hasattr(rel, 'source') else None
                    target_id = getattr(rel.target, 'id', None) if hasattr(rel, 'target') else None
                    
                    if source_id and target_id:
                        # 标准化关系两端的节点ID
                        source_id = self.normalize_entity_name(source_id)
                        target_id = self.normalize_entity_name(target_id)
                        
                        if hasattr(rel, 'source'):
                            rel.source.id = source_id
                        if hasattr(rel, 'target'):
                            rel.target.id = target_id
                        
                        # 检查两端节点是否都有效
                        if (self.is_valid_entity(source_id) and 
                            self.is_valid_entity(target_id) and
                            source_id != target_id):  # 避免自环
                            valid_relationships.append(rel)
                
                doc.relationships = valid_relationships
            
            total_nodes_after += len(doc.nodes) if doc.nodes else 0
            total_rels_after += len(doc.relationships) if doc.relationships else 0
            
            # 只保留有节点或关系的文档
            if (doc.nodes and len(doc.nodes) > 0) or (doc.relationships and len(doc.relationships) > 0):
                filtered_docs.append(doc)
        
        logging.info(f"实体优化统计:")
        logging.info(f"  节点: {total_nodes_before} -> {total_nodes_after} (减少 {total_nodes_before - total_nodes_after})")
        logging.info(f"  关系: {total_rels_before} -> {total_rels_after} (减少 {total_rels_before - total_rels_after})")
        logging.info(f"  图文档: {len(graph_documents)} -> {len(filtered_docs)} (减少 {len(graph_documents) - len(filtered_docs)})")
        
        return filtered_docs
    
    def merge_duplicate_entities(self, graph_documents: List[Any]) -> List[Any]:
        """
        合并重复的实体
        
        Args:
            graph_documents: 图文档列表
            
        Returns:
            合并后的图文档列表
        """
        # 统计所有实体
        entity_count = defaultdict(int)
        
        for doc in graph_documents:
            if doc.nodes:
                for node in doc.nodes:
                    node_id = getattr(node, 'id', None)
                    if node_id:
                        entity_count[node_id] += 1
        
        # 记录重复实体
        duplicate_entities = {k: v for k, v in entity_count.items() if v > 1}
        
        if duplicate_entities:
            logging.info(f"发现 {len(duplicate_entities)} 个重复实体（出现次数>1）")
            # 显示前10个最常见的实体
            top_entities = sorted(duplicate_entities.items(), key=lambda x: x[1], reverse=True)[:10]
            for entity, count in top_entities:
                logging.info(f"  {entity}: {count}次")
        
        return graph_documents
    
    def get_entity_statistics(self, graph_documents: List[Any]) -> Dict[str, Any]:
        """
        获取实体统计信息
        
        Args:
            graph_documents: 图文档列表
            
        Returns:
            统计信息字典
        """
        stats = {
            'total_documents': len(graph_documents),
            'total_nodes': 0,
            'total_relationships': 0,
            'entity_types': defaultdict(int),
            'relationship_types': defaultdict(int),
            'empty_documents': 0
        }
        
        for doc in graph_documents:
            if not doc.nodes and not doc.relationships:
                stats['empty_documents'] += 1
                continue
            
            if doc.nodes:
                stats['total_nodes'] += len(doc.nodes)
                for node in doc.nodes:
                    node_type = getattr(node, 'type', 'Unknown')
                    stats['entity_types'][node_type] += 1
            
            if doc.relationships:
                stats['total_relationships'] += len(doc.relationships)
                for rel in doc.relationships:
                    rel_type = getattr(rel, 'type', 'Unknown')
                    stats['relationship_types'][rel_type] += 1
        
        return stats
    
    def print_statistics(self, stats: Dict[str, Any]):
        """
        打印统计信息
        
        Args:
            stats: 统计信息字典
        """
        logging.info("=" * 60)
        logging.info("知识图谱提取统计")
        logging.info("=" * 60)
        logging.info(f"总文档数: {stats['total_documents']}")
        logging.info(f"空文档数: {stats['empty_documents']}")
        logging.info(f"总节点数: {stats['total_nodes']}")
        logging.info(f"总关系数: {stats['total_relationships']}")
        
        if stats['entity_types']:
            logging.info("\n实体类型分布:")
            for entity_type, count in sorted(stats['entity_types'].items(), key=lambda x: x[1], reverse=True):
                logging.info(f"  {entity_type}: {count}")
        
        if stats['relationship_types']:
            logging.info("\n关系类型分布:")
            for rel_type, count in sorted(stats['relationship_types'].items(), key=lambda x: x[1], reverse=True)[:10]:
                logging.info(f"  {rel_type}: {count}")
        
        logging.info("=" * 60)


def optimize_graph_documents(graph_documents: List[Any]) -> List[Any]:
    """
    优化图文档（主函数）
    
    Args:
        graph_documents: 原始图文档列表
        
    Returns:
        优化后的图文档列表
    """
    optimizer = EntityOptimizer()
    
    # 1. 过滤无效实体
    logging.info("开始优化图文档...")
    filtered_docs = optimizer.filter_graph_documents(graph_documents)
    
    # 2. 合并重复实体
    merged_docs = optimizer.merge_duplicate_entities(filtered_docs)
    
    # 3. 获取并打印统计信息
    stats = optimizer.get_entity_statistics(merged_docs)
    optimizer.print_statistics(stats)
    
    return merged_docs

