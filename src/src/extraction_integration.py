# -*- coding: utf-8 -*-
"""
集成模块：将康复训练提取集成到LLM处理流程
支持自动检测文档类型并应用相应的提取策略
"""

import logging
from typing import List, Tuple, Optional
from langchain_core.documents import Document

logging.basicConfig(format='%(asctime)s - %(message)s', level='INFO')


class DocumentTypeDetector:
    """文档类型检测器"""
    
    @staticmethod
    def detect_document_type(text: str) -> str:
        """
        检测文档类型：康复训练、医学、通用等
        """
        # 康复训练文档特征（增加更多关键词变体）
        rehabilitation_keywords = [
            '训练', '康复', '强化', '拉伸', '屈伸', '旋转',
            '组数', '次数', '组', '次',  # 添加"组"和"次"
            '频率', '强度', '阶段',
            '功能改善', '症状缓解', '预防', '恢复',
            '颈椎', '胸椎', '腰椎', '脊柱',
            '肌肉', '关节', '姿态', '姿势',
            '动作', '锻炼', '运动', '练习'
        ]
        
        # 医学文档特征
        medical_keywords = ['病因', '症状', '诊断', '治疗', '药物', '疾病']
        
        # 计算康复关键词出现频率
        rehab_score = sum(1 for keyword in rehabilitation_keywords if keyword in text)
        medical_score = sum(1 for keyword in medical_keywords if keyword in text)
        
        # 降低阈值，提高识别准确性
        if rehab_score >= 3:
            return 'rehabilitation'
        elif medical_score >= 2:
            return 'medical'
        else:
            return 'general'
    
    @staticmethod
    def get_extraction_config(doc_type: str) -> dict:
        """根据文档类型获取提取配置"""
        if doc_type == 'rehabilitation':
            from src.rehabilitation_extraction_config import (
                REHABILITATION_EXTRACTION_PROMPT,
                get_rehabilitation_allowed_nodes,
                get_rehabilitation_allowed_relationships
            )
            return {
                'prompt': REHABILITATION_EXTRACTION_PROMPT,
                'allowed_nodes': get_rehabilitation_allowed_nodes(),
                'allowed_relationships': get_rehabilitation_allowed_relationships(),
                'type': 'rehabilitation'
            }
        elif doc_type == 'medical':
            from src.medical_extraction_config import (
                CHINESE_MEDICAL_EXTRACTION_PROMPT,
                get_medical_allowed_nodes,
                get_medical_allowed_relationships
            )
            return {
                'prompt': CHINESE_MEDICAL_EXTRACTION_PROMPT,
                'allowed_nodes': get_medical_allowed_nodes(),
                'allowed_relationships': get_medical_allowed_relationships(),
                'type': 'medical'
            }
        else:
            return {
                'prompt': '',
                'allowed_nodes': '',
                'allowed_relationships': '',
                'type': 'general'
            }


class EnhancedExtractionPipeline:
    """增强的提取管道"""
    
    def __init__(self):
        self.detector = DocumentTypeDetector()
    
    def process_documents(self, documents: List[Document], doc_type: Optional[str] = None) -> Tuple[List[Document], dict]:
        """
        处理文档，返回增强后的文档和配置信息
        """
        if not documents:
            return documents, {}
        
        # 检测文档类型
        sample_text = ' '.join([doc.page_content[:500] for doc in documents[:3]])
        detected_type = doc_type or self.detector.detect_document_type(sample_text)
        
        logging.info(f"检测到文档类型: {detected_type}")
        
        # 获取提取配置
        config = self.detector.get_extraction_config(detected_type)
        
        # 如果是康复训练文档，进行增强处理
        if detected_type == 'rehabilitation':
            documents = self._enhance_rehabilitation_documents(documents)
        
        return documents, config
    
    def _enhance_rehabilitation_documents(self, documents: List[Document]) -> List[Document]:
        """
        增强康复训练文档的处理
        """
        from src.enhanced_extraction import (
            RehabilitationEntityExtractor,
            extract_detailed_relationships
        )
        
        enhanced_docs = []
        extractor = RehabilitationEntityExtractor()
        
        for doc in documents:
            text = doc.page_content
            
            # 提取训练参数
            parameters = extractor.extract_training_parameters(text)
            muscles = extractor.extract_muscle_groups(text)
            locations = extractor.extract_anatomical_locations(text)
            goals = extractor.extract_training_goals(text)
            phases = extractor.extract_rehabilitation_phases(text)
            contraindications = extractor.extract_contraindications(text)
            
            # 添加元数据
            metadata = doc.metadata.copy() if doc.metadata else {}
            metadata['extracted_parameters'] = parameters
            metadata['extracted_muscles'] = muscles
            metadata['extracted_locations'] = locations
            metadata['extracted_goals'] = goals
            metadata['extracted_phases'] = phases
            metadata['extracted_contraindications'] = contraindications
            metadata['doc_type'] = 'rehabilitation'
            
            # 创建增强的文档
            enhanced_doc = Document(
                page_content=text,
                metadata=metadata
            )
            enhanced_docs.append(enhanced_doc)
            
            logging.info(f"增强文档: 参数={len(parameters)}, 肌肉={len(muscles)}, "
                        f"部位={len(locations)}, 目标={len(goals)}, 阶段={len(phases)}")
        
        return enhanced_docs


def get_enhanced_additional_instructions(doc_type: str, additional_instructions: Optional[str] = None) -> str:
    """
    获取增强的附加指令
    """
    if doc_type == 'rehabilitation':
        from src.rehabilitation_extraction_config import REHABILITATION_EXTRACTION_PROMPT
        base_prompt = REHABILITATION_EXTRACTION_PROMPT
    elif doc_type == 'medical':
        from src.medical_extraction_config import CHINESE_MEDICAL_EXTRACTION_PROMPT
        base_prompt = CHINESE_MEDICAL_EXTRACTION_PROMPT
    else:
        base_prompt = ""
    
    if additional_instructions:
        return base_prompt + "\n\n" + additional_instructions
    return base_prompt


def create_parameter_nodes_and_relationships(graph_documents: List, 
                                            extracted_metadata: dict) -> List:
    """
    根据提取的元数据创建参数节点和关系
    """
    from langchain_core.graph_document import Node, Relationship
    
    for graph_doc in graph_documents:
        # 添加参数节点
        parameters = extracted_metadata.get('extracted_parameters', {})
        for param_type, param_values in parameters.items():
            for param_value in param_values:
                param_node = Node(
                    id=param_value,
                    type=_map_param_type(param_type)
                )
                if param_node not in graph_doc.nodes:
                    graph_doc.nodes.append(param_node)
        
        # 添加肌肉群节点
        for muscle in extracted_metadata.get('extracted_muscles', []):
            muscle_node = Node(id=muscle, type='肌肉群')
            if muscle_node not in graph_doc.nodes:
                graph_doc.nodes.append(muscle_node)
        
        # 添加解剖部位节点
        for location in extracted_metadata.get('extracted_locations', []):
            location_node = Node(id=location, type='解剖部位')
            if location_node not in graph_doc.nodes:
                graph_doc.nodes.append(location_node)
        
        # 添加训练目标节点
        for goal in extracted_metadata.get('extracted_goals', []):
            goal_node = Node(id=goal, type='训练目标')
            if goal_node not in graph_doc.nodes:
                graph_doc.nodes.append(goal_node)
        
        # 添加康复阶段节点
        for phase in extracted_metadata.get('extracted_phases', []):
            phase_node = Node(id=phase, type='康复阶段')
            if phase_node not in graph_doc.nodes:
                graph_doc.nodes.append(phase_node)
    
    return graph_documents


def _map_param_type(param_type: str) -> str:
    """映射参数类型到实体类型"""
    mapping = {
        'sets': '组数',
        'reps': '次数',
        'intensity': '训练强度',
        'frequency': '训练频率',
        'duration': '持续时间',
        'rest_time': '休息时间'
    }
    return mapping.get(param_type, '训练参数')

