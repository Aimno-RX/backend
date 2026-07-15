# -*- coding: utf-8 -*-
"""
高级三元组提取模块 - 针对康复训练文档的细粒度实体和关系提取
支持多层次、多维度的知识图谱构建
"""

import logging
import re
from typing import List, Dict, Tuple, Set, Optional
from collections import defaultdict
from dataclasses import dataclass

logging.basicConfig(format='%(asctime)s - %(message)s', level='INFO')


@dataclass
class Triplet:
    """三元组数据结构"""
    source: str
    relation: str
    target: str
    confidence: float = 1.0
    source_type: str = ""
    target_type: str = ""
    evidence: str = ""  # 提取证据


class AdvancedRehabilitationExtractor:
    """高级康复训练三元组提取器"""
    
    def __init__(self):
        self.triplets: List[Triplet] = []
        self.entities: Dict[str, Set[str]] = defaultdict(set)
        self.seen_triplets: Set[Tuple] = set()
        
        # 初始化各类型的模式库
        self._init_patterns()
    
    def _init_patterns(self):
        """初始化提取模式"""
        # 训练动作关键词
        self.action_keywords = {
            '屈伸': '颈部屈伸',
            '旋转': '颈部旋转',
            '侧屈': '颈部侧屈',
            '拉伸': '拉伸训练',
            '耸动': '肩部耸动',
            '外旋': '肩部外旋',
            '内旋': '肩部内旋',
            '上抬': '上肢上抬',
            '下压': '下压训练',
            '前推': '前推训练',
            '后拉': '后拉训练',
            '转动': '转动训练',
            '摆动': '摆动训练',
            '抖动': '抖动训练',
            '收缩': '肌肉收缩',
            '放松': '肌肉放松',
            '稳定': '稳定训练',
            '强化': '强化训练',
        }
        
        # 肌肉群映射
        self.muscle_groups = {
            '颈部肌肉': ['颈部', '颈肌'],
            '斜方肌': ['斜方肌', '上斜方肌', '中斜方肌', '下斜方肌'],
            '菱形肌': ['菱形肌'],
            '胸大肌': ['胸大肌'],
            '胸小肌': ['胸小肌'],
            '背阔肌': ['背阔肌'],
            '竖脊肌': ['竖脊肌', '脊柱竖立肌'],
            '腹直肌': ['腹直肌'],
            '腹外斜肌': ['腹外斜肌'],
            '腹内斜肌': ['腹内斜肌'],
            '肩袖肌群': ['肩袖肌群', '旋转肌群'],
            '前锯肌': ['前锯肌'],
            '肩胛提肌': ['肩胛提肌'],
            '核心肌群': ['核心肌群', '深层稳定肌'],
        }
        
        # 解剖部位映射
        self.anatomical_locations = {
            '颈椎': ['颈椎', 'C1-C7', '颈椎体'],
            '胸椎': ['胸椎', 'T1-T12', '胸椎体'],
            '腰椎': ['腰椎', 'L1-L5'],
            '脊柱': ['脊柱', '脊椎', '脊骨'],
            '肩关节': ['肩关节', '肩部'],
            '肩胛骨': ['肩胛骨', '肩甲骨'],
            '肩锁关节': ['肩锁关节', 'AC关节'],
            '胸肋关节': ['胸肋关节'],
            '椎间盘': ['椎间盘', '椎间盘突出'],
            '椎体': ['椎体'],
            '脊髓': ['脊髓'],
        }
        
        # 训练目标
        self.training_goals = {
            '增强肌力': ['增强肌力', '肌力增强', '力量增强'],
            '改善柔韧性': ['改善柔韧性', '柔韧性改善', '灵活性增加'],
            '增加稳定性': ['增加稳定性', '稳定性增加', '脊柱稳定'],
            '改善姿态': ['改善姿态', '姿态纠正', '姿势改善'],
            '缓解疼痛': ['缓解疼痛', '疼痛缓解', '止痛'],
            '预防复发': ['预防复发', '防止复发'],
            '增加活动度': ['增加活动度', '活动范围增加', '活动度改善'],
            '改善功能': ['改善功能', '功能恢复', '功能改善'],
            '增强耐力': ['增强耐力', '耐力增强'],
            '改善协调性': ['改善协调性', '协调性增加'],
        }
        
        # 康复阶段
        self.rehabilitation_phases = {
            '急性期': ['急性期', '发病初期', '炎症期', '早期'],
            '亚急性期': ['亚急性期', '恢复初期', '过渡期'],
            '慢性期': ['慢性期', '长期阶段', '稳定期'],
            '恢复期': ['恢复期', '功能恢复期', '回归期'],
        }
    
    def extract_all_triplets(self, text: str) -> List[Triplet]:
        """
        从文本中提取所有三元组
        """
        self.triplets = []
        self.entities = defaultdict(set)
        self.seen_triplets = set()
        
        # 分段处理文本
        sentences = self._split_sentences(text)
        
        for sentence in sentences:
            if len(sentence.strip()) < 5:
                continue
            
            # 多层次提取
            self._extract_action_triplets(sentence)
            self._extract_parameter_triplets(sentence)
            self._extract_anatomical_triplets(sentence)
            self._extract_goal_triplets(sentence)
            self._extract_phase_triplets(sentence)
            self._extract_contraindication_triplets(sentence)
            self._extract_relationship_triplets(sentence)
        
        logging.info(f"总共提取 {len(self.triplets)} 个三元组")
        return self.triplets
    
    def _split_sentences(self, text: str) -> List[str]:
        """按句号、逗号等分割文本"""
        # 保留中文标点符号
        sentences = re.split(r'[。！？；，、\n]', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _extract_action_triplets(self, sentence: str):
        """提取训练动作相关的三元组"""
        # 查找动作关键词
        for keyword, action_name in self.action_keywords.items():
            if keyword in sentence:
                # 动作本身
                self._add_entity('训练动作', action_name)
                
                # 提取动作类型
                if '拉伸' in keyword:
                    self._add_triplet(action_name, '属于类型', '拉伸训练', '训练动作', '动作类型', sentence)
                elif '强化' in keyword or '屈伸' in keyword or '旋转' in keyword:
                    self._add_triplet(action_name, '属于类型', '强化训练', '训练动作', '动作类型', sentence)
                elif '稳定' in keyword:
                    self._add_triplet(action_name, '属于类型', '稳定训练', '训练动作', '动作类型', sentence)
                
                # 提取难度等级
                if '简单' in sentence or '基础' in sentence or '初级' in sentence:
                    self._add_triplet(action_name, '难度等级', '低难度', '训练动作', '动作难度', sentence)
                elif '中等' in sentence or '中级' in sentence:
                    self._add_triplet(action_name, '难度等级', '中等难度', '训练动作', '动作难度', sentence)
                elif '高级' in sentence or '进阶' in sentence or '加强' in sentence:
                    self._add_triplet(action_name, '难度等级', '高难度', '训练动作', '动作难度', sentence)
    
    def _extract_parameter_triplets(self, sentence: str):
        """提取训练参数三元组"""
        # 查找所有训练动作
        actions = self._find_actions_in_sentence(sentence)
        
        for action in actions:
            # 提取组数
            sets_match = re.search(r'(\d+)\s*组(?!合)', sentence)
            if sets_match:
                sets_value = f"{sets_match.group(1)}组"
                self._add_entity('组数', sets_value)
                self._add_triplet(action, '标准组数', sets_value, '训练动作', '组数', sentence)
            
            # 提取次数
            reps_patterns = [
                r'(?:每组)?(\d+[-~]?\d*)\s*次(?!数)',
                r'(\d+[-~]?\d*)\s*reps',
            ]
            for pattern in reps_patterns:
                reps_match = re.search(pattern, sentence)
                if reps_match:
                    reps_value = f"{reps_match.group(1)}次"
                    self._add_entity('次数', reps_value)
                    self._add_triplet(action, '标准次数', reps_value, '训练动作', '次数', sentence)
            
            # 提取强度
            intensity_patterns = [
                (r'轻度|低强度', '轻度'),
                (r'中等|中等强度', '中等强度'),
                (r'重度|高强度', '高强度'),
                (r'(\d+%\s*最大强度)', None),
            ]
            for pattern, intensity_name in intensity_patterns:
                if re.search(pattern, sentence):
                    intensity = intensity_name or re.search(pattern, sentence).group(1)
                    self._add_entity('训练强度', intensity)
                    self._add_triplet(action, '推荐强度', intensity, '训练动作', '训练强度', sentence)
            
            # 提取频率
            freq_patterns = [
                (r'每天', '每天'),
                (r'每周', '每周'),
                (r'(\d+)\s*次\s*/\s*(天|周|月)', None),
            ]
            for pattern, freq_name in freq_patterns:
                freq_match = re.search(pattern, sentence)
                if freq_match:
                    frequency = freq_name or f"{freq_match.group(1)}次/{freq_match.group(2)}"
                    self._add_entity('训练频率', frequency)
                    self._add_triplet(action, '推荐频率', frequency, '训练动作', '训练频率', sentence)
            
            # 提取持续时间
            duration_patterns = [
                r'(?:停留|持续|保持)?(\d+)\s*秒',
                r'(?:停留|持续|保持)?(\d+)\s*分钟',
            ]
            for pattern in duration_patterns:
                duration_match = re.search(pattern, sentence)
                if duration_match:
                    duration_value = f"{duration_match.group(1)}秒" if '秒' in pattern else f"{duration_match.group(1)}分钟"
                    self._add_entity('持续时间', duration_value)
                    self._add_triplet(action, '持续时间', duration_value, '训练动作', '持续时间', sentence)
            
            # 提取休息时间
            rest_patterns = [
                r'(?:休息|间隔)(\d+)\s*秒',
                r'(?:休息|间隔)(\d+)\s*分钟',
            ]
            for pattern in rest_patterns:
                rest_match = re.search(pattern, sentence)
                if rest_match:
                    rest_value = f"{rest_match.group(1)}秒" if '秒' in pattern else f"{rest_match.group(1)}分钟"
                    self._add_entity('休息时间', rest_value)
                    self._add_triplet(action, '休息间隔', rest_value, '训练动作', '休息时间', sentence)
    
    def _extract_anatomical_triplets(self, sentence: str):
        """提取解剖部位相关三元组"""
        actions = self._find_actions_in_sentence(sentence)
        
        # 查找肌肉群
        for muscle_name, keywords in self.muscle_groups.items():
            for keyword in keywords:
                if keyword in sentence:
                    self._add_entity('肌肉群', muscle_name)
                    for action in actions:
                        self._add_triplet(action, '针对肌肉', muscle_name, '训练动作', '肌肉群', sentence)
        
        # 查找解剖部位
        for location_name, keywords in self.anatomical_locations.items():
            for keyword in keywords:
                if keyword in sentence:
                    self._add_entity('解剖部位', location_name)
                    for action in actions:
                        self._add_triplet(action, '针对部位', location_name, '训练动作', '解剖部位', sentence)
    
    def _extract_goal_triplets(self, sentence: str):
        """提取训练目标三元组"""
        actions = self._find_actions_in_sentence(sentence)
        
        for goal_name, keywords in self.training_goals.items():
            for keyword in keywords:
                if keyword in sentence:
                    self._add_entity('训练目标', goal_name)
                    for action in actions:
                        self._add_triplet(action, '训练目标', goal_name, '训练动作', '训练目标', sentence)
    
    def _extract_phase_triplets(self, sentence: str):
        """提取康复阶段三元组"""
        actions = self._find_actions_in_sentence(sentence)
        
        for phase_name, keywords in self.rehabilitation_phases.items():
            for keyword in keywords:
                if keyword in sentence:
                    self._add_entity('康复阶段', phase_name)
                    for action in actions:
                        self._add_triplet(action, '适用阶段', phase_name, '训练动作', '康复阶段', sentence)
    
    def _extract_contraindication_triplets(self, sentence: str):
        """提取禁忌症和注意事项三元组"""
        # 禁忌症模式
        if '禁忌' in sentence or '避免' in sentence or '不应该' in sentence:
            actions = self._find_actions_in_sentence(sentence)
            
            # 提取禁忌症描述
            contraindication_patterns = [
                r'禁忌[：:](.*?)(?=[。，、]|$)',
                r'(.*?)患者禁忌',
                r'不应该(.*?)(?=[。，、]|$)',
                r'避免(.*?)(?=[。，、]|$)',
            ]
            
            for pattern in contraindication_patterns:
                match = re.search(pattern, sentence)
                if match:
                    contraindication = match.group(1).strip()
                    if contraindication:
                        self._add_entity('禁忌症', contraindication)
                        for action in actions:
                            self._add_triplet(action, '禁忌症', contraindication, '训练动作', '禁忌症', sentence)
        
        # 注意事项
        if '注意' in sentence or '应该' in sentence or '需要' in sentence:
            actions = self._find_actions_in_sentence(sentence)
            
            precaution_patterns = [
                r'注意[：:](.*?)(?=[。，、]|$)',
                r'应该(.*?)(?=[。，、]|$)',
                r'需要(.*?)(?=[。，、]|$)',
            ]
            
            for pattern in precaution_patterns:
                match = re.search(pattern, sentence)
                if match:
                    precaution = match.group(1).strip()
                    if precaution:
                        self._add_entity('注意事项', precaution)
                        for action in actions:
                            self._add_triplet(action, '注意事项', precaution, '训练动作', '注意事项', sentence)
    
    def _extract_relationship_triplets(self, sentence: str):
        """提取其他关系三元组"""
        # 症状相关
        symptoms = ['颈痛', '肩痛', '背痛', '头晕', '麻木', '酸胀', '疼痛']
        for symptom in symptoms:
            if symptom in sentence:
                self._add_entity('症状', symptom)
                
                # 症状与解剖部位的关系
                for location_name, keywords in self.anatomical_locations.items():
                    for keyword in keywords:
                        if keyword in sentence:
                            self._add_triplet(symptom, '位于', location_name, '症状', '解剖部位', sentence)
                
                # 训练与症状缓解的关系
                actions = self._find_actions_in_sentence(sentence)
                if '缓解' in sentence or '改善' in sentence or '减轻' in sentence:
                    for action in actions:
                        self._add_triplet(action, '缓解症状', symptom, '训练动作', '症状', sentence)
    
    def _find_actions_in_sentence(self, sentence: str) -> List[str]:
        """在句子中查找所有训练动作"""
        actions = []
        for keyword, action_name in self.action_keywords.items():
            if keyword in sentence:
                actions.append(action_name)
        return list(set(actions))  # 去重
    
    def _add_entity(self, entity_type: str, entity_name: str):
        """添加实体"""
        self.entities[entity_type].add(entity_name)
    
    def _add_triplet(self, source: str, relation: str, target: str, 
                     source_type: str, target_type: str, evidence: str):
        """添加三元组（去重）"""
        triplet_key = (source, relation, target)
        if triplet_key not in self.seen_triplets:
            self.seen_triplets.add(triplet_key)
            triplet = Triplet(
                source=source,
                relation=relation,
                target=target,
                source_type=source_type,
                target_type=target_type,
                evidence=evidence[:100]  # 保留前100个字符作为证据
            )
            self.triplets.append(triplet)
    
    def get_triplets_by_type(self, source_type: str = None, 
                            target_type: str = None) -> List[Triplet]:
        """按类型筛选三元组"""
        result = self.triplets
        if source_type:
            result = [t for t in result if t.source_type == source_type]
        if target_type:
            result = [t for t in result if t.target_type == target_type]
        return result
    
    def get_entities_by_type(self, entity_type: str) -> Set[str]:
        """获取指定类型的所有实体"""
        return self.entities.get(entity_type, set())
    
    def export_triplets_as_dict(self) -> List[Dict]:
        """导出三元组为字典格式"""
        return [
            {
                'source': t.source,
                'relation': t.relation,
                'target': t.target,
                'source_type': t.source_type,
                'target_type': t.target_type,
                'evidence': t.evidence,
                'confidence': t.confidence
            }
            for t in self.triplets
        ]
    
    def export_entities_as_dict(self) -> Dict[str, List[str]]:
        """导出实体为字典格式"""
        return {
            entity_type: sorted(list(entities))
            for entity_type, entities in self.entities.items()
        }


def extract_rehabilitation_triplets(text: str) -> Tuple[List[Triplet], Dict[str, Set[str]]]:
    """
    主函数：从康复训练文本中提取三元组和实体
    
    Args:
        text: 输入文本
    
    Returns:
        (三元组列表, 实体字典)
    """
    extractor = AdvancedRehabilitationExtractor()
    triplets = extractor.extract_all_triplets(text)
    entities = extractor.entities
    
    logging.info(f"提取完成 - 三元组: {len(triplets)}, 实体类型: {len(entities)}")
    for entity_type, entity_set in entities.items():
        logging.info(f"  {entity_type}: {len(entity_set)} 个")
    
    return triplets, entities

