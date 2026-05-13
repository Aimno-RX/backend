# -*- coding: utf-8 -*-
"""
增强的三元组提取模块
支持康复训练文档的细粒度实体和关系提取
"""

import logging
import re
from typing import List, Dict, Tuple, Set
from langchain_core.documents import Document
from langchain_core.language_model import BaseLanguageModel

logging.basicConfig(format='%(asctime)s - %(message)s', level='INFO')


class RehabilitationEntityExtractor:
    """康复训练专用的实体和关系提取器"""
    
    def __init__(self):
        self.training_actions = set()
        self.parameters = {}
        self.relationships = []
        
    def extract_training_parameters(self, text: str) -> Dict:
        """
        从文本中提取训练参数（组数、次数、强度、频率等）
        """
        parameters = {
            'sets': [],
            'reps': [],
            'intensity': [],
            'frequency': [],
            'duration': [],
            'rest_time': []
        }
        
        # 提取组数：3组、3set、3×10等
        sets_patterns = [
            r'(\d+)\s*组(?!合)',
            r'(\d+)\s*set',
            r'(\d+)\s*×\s*(\d+)',  # 3×10格式
        ]
        for pattern in sets_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    parameters['sets'].append(f"{match[0]}组")
                else:
                    parameters['sets'].append(f"{match}组")
        
        # 提取次数：10次、15-20次、10 reps等
        reps_patterns = [
            r'(?:每组)?(\d+[-~]?\d*)\s*次(?!数)',
            r'(\d+[-~]?\d*)\s*reps',
            r'(\d+[-~]?\d*)\s*repetitions',
        ]
        for pattern in reps_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                parameters['reps'].append(f"{match}次")
        
        # 提取强度：轻度、中等、重度、50%最大强度等
        intensity_patterns = [
            r'(轻度|中等|重度|低强度|中等强度|高强度)',
            r'(\d+%\s*最大强度)',
            r'(RPE\s*\d+)',
        ]
        for pattern in intensity_patterns:
            matches = re.findall(pattern, text)
            parameters['intensity'].extend(matches)
        
        # 提取频率：每天、每周、1次/天、3次/周等
        frequency_patterns = [
            r'(每天|每周|每月)',
            r'(\d+)\s*次\s*/\s*(天|周|月)',
            r'(日常|每日)',
        ]
        for pattern in frequency_patterns:
            matches = re.findall(pattern, text)
            if isinstance(matches[0], tuple) if matches else False:
                for match in matches:
                    parameters['frequency'].append(f"{match[0]}次/{match[1]}")
            else:
                parameters['frequency'].extend(matches)
        
        # 提取持续时间：5秒、30秒、1分钟等
        duration_patterns = [
            r'(?:停留|持续|保持)?(\d+)\s*秒',
            r'(?:停留|持续|保持)?(\d+)\s*分钟',
            r'(\d+\s*-\s*\d+)\s*秒',
        ]
        for pattern in duration_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if '秒' not in str(match):
                    parameters['duration'].append(f"{match}秒")
                else:
                    parameters['duration'].append(str(match))
        
        # 提取休息时间：休息30秒、间隔1分钟等
        rest_patterns = [
            r'(?:休息|间隔)(\d+)\s*秒',
            r'(?:休息|间隔)(\d+)\s*分钟',
        ]
        for pattern in rest_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                parameters['rest_time'].append(f"{match}秒")
        
        # 去重
        for key in parameters:
            parameters[key] = list(set(parameters[key]))
        
        return parameters
    
    def extract_muscle_groups(self, text: str) -> List[str]:
        """提取涉及的肌肉群"""
        muscle_patterns = [
            '颈部肌肉', '斜方肌', '菱形肌', '胸大肌', '胸小肌',
            '背阔肌', '竖脊肌', '腹直肌', '腹外斜肌', '腹内斜肌',
            '肩胛提肌', '前锯肌', '肩袖肌群', '旋转肌群',
            '上背部肌肉', '下背部肌肉', '核心肌群', '深层稳定肌'
        ]
        
        found_muscles = []
        for muscle in muscle_patterns:
            if muscle in text:
                found_muscles.append(muscle)
        
        return found_muscles
    
    def extract_anatomical_locations(self, text: str) -> List[str]:
        """提取解剖部位"""
        anatomy_patterns = [
            '颈椎', '胸椎', '腰椎', '脊柱', '脊髓',
            '肩关节', '肩胛骨', '肩锁关节', '胸肋关节',
            '颈椎关节', '胸椎关节', '椎间盘', '椎体',
            '颈部', '肩部', '背部', '腰部', '胸部'
        ]
        
        found_locations = []
        for location in anatomy_patterns:
            if location in text:
                found_locations.append(location)
        
        return found_locations
    
    def extract_training_goals(self, text: str) -> List[str]:
        """提取训练目标"""
        goal_patterns = [
            '增强肌力', '改善柔韧性', '增加稳定性', '改善姿态',
            '缓解疼痛', '预防复发', '增加活动度', '改善功能',
            '增强耐力', '改善协调性', '增加灵活性', '恢复功能'
        ]
        
        found_goals = []
        for goal in goal_patterns:
            if goal in text:
                found_goals.append(goal)
        
        return found_goals
    
    def extract_rehabilitation_phases(self, text: str) -> List[str]:
        """提取康复阶段"""
        phase_patterns = [
            ('急性期', ['急性期', '发病初期', '炎症期']),
            ('亚急性期', ['亚急性期', '恢复初期', '过渡期']),
            ('慢性期', ['慢性期', '长期阶段', '稳定期']),
            ('恢复期', ['恢复期', '功能恢复期', '回归期']),
        ]
        
        found_phases = []
        for phase_name, keywords in phase_patterns:
            for keyword in keywords:
                if keyword in text:
                    found_phases.append(phase_name)
                    break
        
        return found_phases
    
    def extract_contraindications(self, text: str) -> List[str]:
        """提取禁忌症和注意事项"""
        contraindications = []
        
        # 禁忌症模式
        contraindication_patterns = [
            r'禁忌[：:](.*?)(?:[。，、]|$)',
            r'(.*?)患者禁忌',
            r'不应该(.*?)(?:[。，、]|$)',
            r'避免(.*?)(?:[。，、]|$)',
        ]
        
        for pattern in contraindication_patterns:
            matches = re.findall(pattern, text)
            contraindications.extend(matches)
        
        return [c.strip() for c in contraindications if c.strip()]
    
    def build_relationships(self, action: str, params: Dict, muscles: List[str], 
                           locations: List[str], goals: List[str], phases: List[str]) -> List[Tuple]:
        """构建训练动作与其他实体的关系"""
        relationships = []
        
        # 训练动作 -> 标准组数 -> 组数
        for s in params.get('sets', []):
            relationships.append((action, '标准组数', s))
        
        # 训练动作 -> 标准次数 -> 次数
        for r in params.get('reps', []):
            relationships.append((action, '标准次数', r))
        
        # 训练动作 -> 推荐强度 -> 训练强度
        for intensity in params.get('intensity', []):
            relationships.append((action, '推荐强度', intensity))
        
        # 训练动作 -> 推荐频率 -> 训练频率
        for freq in params.get('frequency', []):
            relationships.append((action, '推荐频率', freq))
        
        # 训练动作 -> 持续时间 -> 持续时间
        for duration in params.get('duration', []):
            relationships.append((action, '持续时间', duration))
        
        # 训练动作 -> 休息间隔 -> 休息时间
        for rest in params.get('rest_time', []):
            relationships.append((action, '休息间隔', rest))
        
        # 训练动作 -> 针对肌肉 -> 肌肉群
        for muscle in muscles:
            relationships.append((action, '针对肌肉', muscle))
        
        # 训练动作 -> 针对部位 -> 解剖部位
        for location in locations:
            relationships.append((action, '针对部位', location))
        
        # 训练动作 -> 训练目标 -> 训练目标
        for goal in goals:
            relationships.append((action, '训练目标', goal))
        
        # 训练动作 -> 适用阶段 -> 康复阶段
        for phase in phases:
            relationships.append((action, '适用阶段', phase))
        
        return relationships


def enhance_graph_documents_with_parameters(graph_documents: List, text: str) -> List:
    """
    增强图文档，添加细粒度的训练参数和关系
    """
    extractor = RehabilitationEntityExtractor()
    
    # 提取训练参数
    parameters = extractor.extract_training_parameters(text)
    muscles = extractor.extract_muscle_groups(text)
    locations = extractor.extract_anatomical_locations(text)
    goals = extractor.extract_training_goals(text)
    phases = extractor.extract_rehabilitation_phases(text)
    contraindications = extractor.extract_contraindications(text)
    
    logging.info(f"提取的参数: 组数={parameters['sets']}, 次数={parameters['reps']}, "
                f"强度={parameters['intensity']}, 频率={parameters['frequency']}")
    logging.info(f"提取的肌肉群: {muscles}")
    logging.info(f"提取的解剖部位: {locations}")
    logging.info(f"提取的训练目标: {goals}")
    logging.info(f"提取的康复阶段: {phases}")
    logging.info(f"提取的禁忌事项: {contraindications}")
    
    # 为每个图文档添加增强的关系
    for graph_doc in graph_documents:
        # 添加参数节点和关系
        for param_type, param_values in parameters.items():
            for param_value in param_values:
                # 创建参数节点
                from langchain_core.graph_document import Node
                param_node = Node(id=param_value, type=_get_param_type(param_type))
                if param_node not in graph_doc.nodes:
                    graph_doc.nodes.append(param_node)
        
        # 添加肌肉群节点
        for muscle in muscles:
            from langchain_core.graph_document import Node
            muscle_node = Node(id=muscle, type='肌肉群')
            if muscle_node not in graph_doc.nodes:
                graph_doc.nodes.append(muscle_node)
        
        # 添加解剖部位节点
        for location in locations:
            from langchain_core.graph_document import Node
            location_node = Node(id=location, type='解剖部位')
            if location_node not in graph_doc.nodes:
                graph_doc.nodes.append(location_node)
        
        # 添加训练目标节点
        for goal in goals:
            from langchain_core.graph_document import Node
            goal_node = Node(id=goal, type='训练目标')
            if goal_node not in graph_doc.nodes:
                graph_doc.nodes.append(goal_node)
        
        # 添加康复阶段节点
        for phase in phases:
            from langchain_core.graph_document import Node
            phase_node = Node(id=phase, type='康复阶段')
            if phase_node not in graph_doc.nodes:
                graph_doc.nodes.append(phase_node)
    
    return graph_documents


def _get_param_type(param_type: str) -> str:
    """获取参数类型对应的实体类型"""
    type_mapping = {
        'sets': '组数',
        'reps': '次数',
        'intensity': '训练强度',
        'frequency': '训练频率',
        'duration': '持续时间',
        'rest_time': '休息时间'
    }
    return type_mapping.get(param_type, '训练参数')


def extract_detailed_relationships(text: str) -> List[Tuple[str, str, str]]:
    """
    从文本中提取详细的三元组关系
    返回格式：[(源实体, 关系, 目标实体), ...]
    """
    relationships = []
    extractor = RehabilitationEntityExtractor()
    
    # 提取所有训练动作（简单启发式方法）
    action_keywords = [
        '屈伸', '旋转', '侧屈', '拉伸', '耸动', '外旋', '内旋',
        '上抬', '下压', '前推', '后拉', '转动', '摆动', '抖动'
    ]
    
    training_actions = []
    for keyword in action_keywords:
        if keyword in text:
            # 提取包含该关键词的短语
            pattern = rf'[^。，、；]*{keyword}[^。，、；]*'
            matches = re.findall(pattern, text)
            training_actions.extend(matches)
    
    # 为每个训练动作提取关系
    for action in training_actions:
        action = action.strip()
        if len(action) > 50:  # 过滤过长的短语
            continue
        
        # 提取该动作的参数
        params = extractor.extract_training_parameters(action)
        muscles = extractor.extract_muscle_groups(action)
        locations = extractor.extract_anatomical_locations(action)
        goals = extractor.extract_training_goals(action)
        phases = extractor.extract_rehabilitation_phases(action)
        
        # 构建关系
        action_relationships = extractor.build_relationships(
            action, params, muscles, locations, goals, phases
        )
        relationships.extend(action_relationships)
    
    return relationships

