# -*- coding: utf-8 -*-
"""
康复训练专用三元组提取器
针对《颈椎胸椎功能强化训练》等康复指导文档的深度提取
"""

import re
from typing import List, Tuple, Dict, Set
from dataclasses import dataclass

@dataclass
class Triplet:
    """三元组数据结构"""
    source: str
    relation: str
    target: str
    confidence: float = 1.0
    source_type: str = ""
    target_type: str = ""
    sentence_id: str = ""
    paragraph_id: str = ""
    page_number: int = 0
    extraction_method: str = "rule"

class RehabilitationTripletExtractor:
    """康复训练三元组提取器"""
    
    # 康复训练相关的实体类型
    EXERCISE_KEYWORDS = {
        '屈伸', '旋转', '侧弯', '耸肩', '拉伸', '按摩', '推拿', '敲打',
        '摇晃', '转圈', '弯腰', '抬头', '低头', '转头', '点头', '摇头',
        '握拳', '伸臂', '举臂', '放松', '收缩', '挤压', '揉搓', '拍打',
        '滚动', '摆动', '晃动', '扭转', '弹拨', '推按', '点按', '叩击',
    }
    
    BODY_PARTS = {
        '颈部', '颈椎', '肩部', '肩膀', '背部', '腰部', '腰椎', '胸部', '胸椎',
        '头部', '头颈', '上肢', '下肢', '四肢', '躯干', '脊柱', '脊椎',
        '肌肉', '关节', '韧带', '骨骼', '神经', '血管',
        '颈肌', '肩肌', '背肌', '腰肌', '腹肌', '胸肌',
        '颈后肌群', '颈前肌群', '肩胛肌', '斜方肌', '菱形肌',
    }
    
    FREQUENCY_KEYWORDS = {
        '每天', '每周', '每月', '每次', '每组', '每日', '日常',
        '次', '组', '遍', '下', '回', '轮', '分钟', '秒', '小时',
    }
    
    POSTURE_KEYWORDS = {
        '坐姿', '站姿', '卧姿', '仰卧', '俯卧', '侧卧', '跪姿',
        '盘腿', '直腿', '弯腿', '挺胸', '收腹', '放松', '紧张',
        '双手', '单手', '双腿', '单腿', '双肩', '单肩',
    }
    
    EFFECT_KEYWORDS = {
        '缓解', '改善', '增强', '提高', '促进', '舒缓', '放松', '恢复',
        '预防', '减少', '消除', '缓解', '治疗', '康复', '锻炼', '保健',
        '强化', '加强', '改善', '改进', '优化', '调理', '调节', '调整',
    }
    
    INTENSITY_KEYWORDS = {
        '轻', '中', '重', '缓慢', '快速', '温和', '剧烈', '适度',
        '逐渐', '循序渐进', '由浅入深', '由易到难',
    }
    
    PRECAUTION_KEYWORDS = {
        '注意', '避免', '不要', '禁止', '切勿', '防止', '小心', '谨慎',
        '保持', '维持', '保证', '确保', '不能', '不可', '不应',
    }
    
    def __init__(self):
        self.triplets: List[Triplet] = []
        self.entities: Dict[str, Set[str]] = {
            '训练动作': set(),
            '解剖部位': set(),
            '频次': set(),
            '姿势': set(),
            '效果': set(),
            '强度': set(),
            '注意事项': set(),
        }
    
    def extract_triplets(self, text: str) -> Tuple[List[Triplet], Dict[str, Set[str]]]:
        """
        从文本中提取康复训练三元组
        """
        self.triplets = []
        self.entities = {k: set() for k in self.entities.keys()}
        
        # 分句处理
        sentences = self._split_sentences(text)
        
        for sentence in sentences:
            self._extract_from_sentence(sentence)
        
        return self.triplets, self.entities
    def extract_triplets_from_sentence_units(self, sentence_units) -> Tuple[List[Triplet], Dict[str, Set[str]]]:
        """
        从结构化句子列表中提取康复训练三元组
        sentence_units 中每个元素应至少包含：
        - text
        - sentence_id
        - paragraph_id
        - page_number
        - labels（可选）
        """
        self.triplets = []
        self.entities = {k: set() for k in self.entities.keys()}

        for sentence_unit in sentence_units:
            self._extract_from_sentence(
                sentence=getattr(sentence_unit, "text", ""),
                sentence_id=getattr(sentence_unit, "sentence_id", ""),
                paragraph_id=getattr(sentence_unit, "paragraph_id", ""),
                page_number=getattr(sentence_unit, "page_number", 0),
                labels=getattr(sentence_unit, "labels", []),
            )

        return self.triplets, self.entities
    def _split_sentences(self, text: str) -> List[str]:
        """分句并保留康复文档中的结构块"""
        text = re.sub(r'\r\n?', '\n', text)
        text = re.sub(r'([：:])', r'\1\n', text)
        text = re.sub(r'(?=(?:练习[一二三四五六七八九十\d]+|第[一二三四五六七八九十\d]+[天周阶段]))', '\n', text)
        text = re.sub(r'(?=\n?\s*(?:[（(]?\d+[)）.]|\-|\•|●))', '\n', text)

        parts = re.split(r'[。！？\n]+', text)
        return [p.strip() for p in parts if p and p.strip()]
    
    def _extract_from_sentence(
        self,
        sentence: str,
        sentence_id: str = "",
        paragraph_id: str = "",
        page_number: int = 0,
        labels=None,
        ):
        """从单句中提取三元组"""
        if len(sentence) < 3:
            return
        
        # 1. 提取训练动作
        exercises = self._extract_exercises(sentence)
        
        # 2. 提取身体部位
        body_parts = self._extract_body_parts(sentence)
        
        # 3. 提取频次信息
        frequencies = self._extract_frequencies(sentence)
        
        # 4. 提取姿势信息
        postures = self._extract_postures(sentence)
        
        # 5. 提取效果信息
        effects = self._extract_effects(sentence)
        
        # 6. 提取强度信息
        intensities = self._extract_intensities(sentence)
        
        # 7. 提取注意事项
        precautions = self._extract_precautions(sentence)
        
        # 8. 构建三元组关系
        self._build_triplets(
            sentence=sentence,
            exercises=exercises,
            body_parts=body_parts,
            frequencies=frequencies,
            postures=postures,
            effects=effects,
            intensities=intensities,
            precautions=precautions,
            sentence_id=sentence_id,
            paragraph_id=paragraph_id,
            page_number=page_number,
            labels=labels or [],
        )
    
    def _extract_exercises(self, sentence: str) -> List[str]:
        """提取训练动作"""
        exercises = []
        
        # 方法1：直接匹配关键词
        for keyword in self.EXERCISE_KEYWORDS:
            if keyword in sentence:
                # 提取包含该关键词的词组
                pattern = f'[\\w\\u4e00-\\u9fff]*{keyword}[\\w\\u4e00-\\u9fff]*'
                matches = re.findall(pattern, sentence)
                exercises.extend(matches)
        
        # 方法2：匹配"X训练"、"X动作"、"X操"等模式
        patterns = [
            r'([\\u4e00-\\u9fff]+(?:训练|动作|操|运动|锻炼|练习))',
            r'([\\u4e00-\\u9fff]*(?:屈伸|旋转|侧弯|耸肩|拉伸|按摩|推拿)[\\u4e00-\\u9fff]*)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, sentence)
            exercises.extend(matches)
        
        # 去重并存储
        exercises = list(set(exercises))
        self.entities['训练动作'].update(exercises)
        
        return exercises
    
    def _extract_body_parts(self, sentence: str) -> List[str]:
        """提取身体部位"""
        body_parts = []
        
        for part in self.BODY_PARTS:
            if part in sentence:
                body_parts.append(part)
        
        self.entities['解剖部位'].update(body_parts)
        return body_parts
    
    def _extract_frequencies(self, sentence: str) -> List[str]:
        """提取频次/时长/次数信息"""
        frequencies = []

        patterns = [
            r'(每[天周月日]\s*\d+\s*[次组遍下回轮])',
            r'(每组\s*\d+\s*[次遍下回])',
            r'(\d+\s*[次组遍下回轮])',
            r'(保持\s*\d+\s*[秒分钟])',
            r'(持续\s*\d+\s*[秒分钟])',
            r'(\d+\s*[秒分钟小时])',
            r'(左右各\s*\d+\s*[次遍下回])',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, sentence)
            for match in matches:
                frequencies.append(re.sub(r'\s+', '', match))

        frequencies = list(set(frequencies))
        self.entities['频次'].update(frequencies)
        return frequencies
    def _extract_postures(self, sentence: str) -> List[str]:
        """提取姿势信息"""
        postures = []
        
        for posture in self.POSTURE_KEYWORDS:
            if posture in sentence:
                postures.append(posture)
        
        self.entities['姿势'].update(postures)
        return postures
    
    def _extract_effects(self, sentence: str) -> List[str]:
        """提取效果信息"""
        effects = []
        
        for effect_kw in self.EFFECT_KEYWORDS:
            if effect_kw in sentence:
                # 提取"效果关键词+目标"的模式
                pattern = f'{effect_kw}([\\u4e00-\\u9fff]+)'
                matches = re.findall(pattern, sentence)
                for match in matches:
                    effects.append(f"{effect_kw}{match}")
        
        self.entities['效果'].update(effects)
        return effects
    
    def _extract_intensities(self, sentence: str) -> List[str]:
        """提取强度信息"""
        intensities = []
        
        for intensity in self.INTENSITY_KEYWORDS:
            if intensity in sentence:
                intensities.append(intensity)
        
        self.entities['强度'].update(intensities)
        return intensities
    
    def _extract_precautions(self, sentence: str) -> List[str]:
        """提取注意事项"""
        precautions = []
        
        for precaution_kw in self.PRECAUTION_KEYWORDS:
            if precaution_kw in sentence:
                # 提取"注意事项关键词+内容"的模式
                pattern = f'{precaution_kw}([\\u4e00-\\u9fff]+)'
                matches = re.findall(pattern, sentence)
                for match in matches:
                    precautions.append(f"{precaution_kw}{match}")
        
        self.entities['注意事项'].update(precautions)
        return precautions
    
    def _build_triplets(self,
        sentence: str,
        exercises: List[str],
        body_parts: List[str],
        frequencies: List[str],
        postures: List[str],
        effects: List[str],
        intensities: List[str],
        precautions: List[str],
        sentence_id: str = "",
        paragraph_id: str = "",
        page_number: int = 0,
        labels=None,
        ):
        """构建三元组关系"""
        
        # 关系1：训练动作 -> 作用部位 -> 身体部位
        for exercise in exercises:
            for body_part in body_parts:
                self.triplets.append(Triplet(
                    source=exercise,
                    relation="作用部位",
                    target=body_part,
                    source_type="训练动作",
                    target_type="解剖部位",
                    sentence_id=sentence_id,
                    paragraph_id=paragraph_id,
                    page_number=page_number,
                    extraction_method="rule",
                ))
        
        # 关系2：训练动作 -> 频次 -> 频次信息
        for exercise in exercises:
            for frequency in frequencies:
                self.triplets.append(Triplet(
                    source=exercise,
                    relation="频次",
                    target=frequency,
                    source_type="训练动作",
                    target_type="频次",
                    sentence_id=sentence_id,
                    paragraph_id=paragraph_id,
                    page_number=page_number,
                    extraction_method="rule",
                ))
        
        # 关系3：训练动作 -> 起始姿势 -> 姿势
        for exercise in exercises:
            for posture in postures:
                self.triplets.append(Triplet(
                    source=exercise,
                    relation="起始姿势",
                    target=posture,
                    source_type="训练动作",
                    target_type="姿势",
                    sentence_id=sentence_id,
                    paragraph_id=paragraph_id,
                    page_number=page_number,
                    extraction_method="rule",
                ))
        
        # 关系4：训练动作 -> 效果 -> 效果描述
        for exercise in exercises:
            for effect in effects:
                self.triplets.append(Triplet(
                    source=exercise,
                    relation="效果",
                    target=effect,
                    source_type="训练动作",
                    target_type="效果",
                    sentence_id=sentence_id,
                    paragraph_id=paragraph_id,
                    page_number=page_number,
                    extraction_method="rule",
                ))
        
        # 关系5：训练动作 -> 强度 -> 强度描述
        for exercise in exercises:
            for intensity in intensities:
                self.triplets.append(Triplet(
                    source=exercise,
                    relation="强度",
                    target=intensity,
                    source_type="训练动作",
                    target_type="强度",
                    sentence_id=sentence_id,
                    paragraph_id=paragraph_id,
                    page_number=page_number,
                    extraction_method="rule",
                ))
        
        # 关系6：训练动作 -> 注意事项 -> 注意事项描述
        for exercise in exercises:
            for precaution in precautions:
                self.triplets.append(Triplet(
                    source=exercise,
                    relation="注意事项",
                    target=precaution,
                    source_type="训练动作",
                    target_type="注意事项",
                    sentence_id=sentence_id,
                    paragraph_id=paragraph_id,
                    page_number=page_number,
                    extraction_method="rule",
                ))
        
        # 关系7：身体部位 -> 训练目标 -> 效果
        for body_part in body_parts:
            for effect in effects:
                self.triplets.append(Triplet(
                    source=body_part,
                    relation="训练目标",
                    target=effect,
                    source_type="解剖部位",
                    target_type="效果",
                    sentence_id=sentence_id,
                    paragraph_id=paragraph_id,
                    page_number=page_number,
                    extraction_method="rule",
                ))
        
        # 关系8：频次 -> 应用于 -> 训练动作
        for frequency in frequencies:
            for exercise in exercises:
                self.triplets.append(Triplet(
                    source=frequency,
                    relation="应用于",
                    target=exercise,
                    source_type="频次",
                    target_type="训练动作",
                    sentence_id=sentence_id,
                    paragraph_id=paragraph_id,
                    page_number=page_number,
                    extraction_method="rule",
                ))
        # 关系9：姿势 -> 用于 -> 训练动作
        for posture in postures:
            for exercise in exercises:
                self.triplets.append(Triplet(
                    source=posture,
                    relation="用于",
                    target=exercise,
                    source_type="姿势",
                    target_type="训练动作",
                    sentence_id=sentence_id,
                    paragraph_id=paragraph_id,
                    page_number=page_number,
                    extraction_method="rule",
                ))

        # 关系10：效果 -> 针对 -> 身体部位
        for effect in effects:
            for body_part in body_parts:
                self.triplets.append(Triplet(
                    source=effect,
                    relation="针对",
                    target=body_part,
                    source_type="效果",
                    target_type="解剖部位",
                    sentence_id=sentence_id,
                    paragraph_id=paragraph_id,
                    page_number=page_number,
                    extraction_method="rule",
                ))

        # 关系11：强度 -> 应用于 -> 训练动作
        for intensity in intensities:
            for exercise in exercises:
                self.triplets.append(Triplet(
                    source=intensity,
                    relation="应用于",
                    target=exercise,
                    source_type="强度",
                    target_type="训练动作",
                    sentence_id=sentence_id,
                    paragraph_id=paragraph_id,
                    page_number=page_number,
                    extraction_method="rule",
                ))

        # 关系12：注意事项 -> 适用于 -> 训练动作
        for precaution in precautions:
            for exercise in exercises:
                self.triplets.append(Triplet(
                    source=precaution,
                    relation="适用于",
                    target=exercise,
                    source_type="注意事项",
                    target_type="训练动作",
                    sentence_id=sentence_id,
                    paragraph_id=paragraph_id,
                    page_number=page_number,
                    extraction_method="rule",
                ))

def extract_rehabilitation_triplets(text: str) -> Tuple[List[Triplet], Dict[str, Set[str]]]:
    """
    便捷函数：从康复训练文本中提取三元组
    
    Args:
        text: 康复训练文本
    
    Returns:
        (三元组列表, 实体字典)
    """
    extractor = RehabilitationTripletExtractor()
    return extractor.extract_triplets(text)


if __name__ == "__main__":
    # 测试
    test_text = """
    颈部屈伸训练：患者坐姿，头部缓慢向前屈曲，停留5秒，然后缓慢后伸，停留5秒。
    做3组，每组10次，每周3次。该训练可增强颈部肌肉力量，缓解颈痛。
    注意不要过度用力，避免颈部受伤。
    """
    
    triplets, entities = extract_rehabilitation_triplets(test_text)
    
    print("提取的三元组：")
    for triplet in triplets:
        print(f"  ({triplet.source}) -[{triplet.relation}]-> ({triplet.target})")
    
    print("\n提取的实体：")
    for entity_type, entity_set in entities.items():
        if entity_set:
            print(f"  {entity_type}: {entity_set}")

