# -*- coding: utf-8 -*-
"""
康复训练表格数据提取器
专门处理《颈椎胸椎功能强化训练》中的表格和结构化内容
"""

import re
from typing import List, Tuple, Dict
from dataclasses import dataclass

@dataclass
class TableTriplet:
    """表格三元组"""
    source: str
    relation: str
    target: str
    confidence: float = 1.0

class RehabilitationTableExtractor:
    """康复训练表格提取器"""
    
    def __init__(self):
        self.triplets: List[TableTriplet] = []
    
    def extract_from_text(self, text: str) -> List[TableTriplet]:
        """从文本中提取表格数据的三元组"""
        self.triplets = []
        
        # 1. 提取"练习效果"表格
        self._extract_exercise_effects_table(text)
        
        # 2. 提取练习步骤（练习一、练习二等）
        self._extract_exercise_steps(text)
        
        # 3. 提取动作要领
        self._extract_action_points(text)
        
        # 4. 提取注意事项
        self._extract_precautions(text)
        
        # 5. 提取重复次数
        self._extract_repetitions(text)
        
        return self.triplets
    
    def _extract_exercise_effects_table(self, text: str):
        """
        提取练习效果表格
        格式：练习 效果
              一   ·强化腹部和腿部肌肉
                   ·拉伸肩胛带肌群、颈前肌群和颈后肌群
        """
        # 匹配表格模式
        table_pattern = r'练习\s+效果\s+((?:[\u4e00-\u9fff一二三四五六七八九十]+\s+[·•\-]\s*[^\n]+\s*)+)'
        table_match = re.search(table_pattern, text, re.MULTILINE)
        
        if table_match:
            table_content = table_match.group(1)
            
            # 解析每一行
            # 匹配：一  ·强化腹部和腿部肌肉
            row_pattern = r'([\u4e00-\u9fff一二三四五六七八九十]+)\s+([·•\-]\s*[^\n]+(?:\n\s+[·•\-]\s*[^\n]+)*)'
            
            for row_match in re.finditer(row_pattern, table_content):
                exercise_num = row_match.group(1).strip()
                effects_text = row_match.group(2).strip()
                
                # 提取所有效果项（以·或•开头）
                effect_pattern = r'[·•\-]\s*([^\n·•\-]+)'
                effects = re.findall(effect_pattern, effects_text)
                
                for effect in effects:
                    effect = effect.strip()
                    if effect:
                        # 创建三元组：练习X -> 效果 -> 具体效果
                        self.triplets.append(TableTriplet(
                            source=f"练习{exercise_num}",
                            relation="效果",
                            target=effect
                        ))
                        
                        # 进一步解析效果中的动作和部位
                        self._parse_effect_details(f"练习{exercise_num}", effect)
    
    def _parse_effect_details(self, exercise_name: str, effect: str):
        """解析效果详情，提取动作和部位"""
        # 匹配：强化/拉伸 + 部位
        action_pattern = r'(强化|拉伸|增强|改善|缓解|放松|锻炼|训练)([^\s，、和]+(?:[、，和][^\s，、和]+)*)'
        
        for match in re.finditer(action_pattern, effect):
            action = match.group(1)
            parts_text = match.group(2)
            
            # 分割部位（用、，和分隔）
            parts = re.split(r'[、，和]', parts_text)
            
            for part in parts:
                part = part.strip()
                if part and len(part) > 1:
                    # 练习X -> 强化/拉伸 -> 部位
                    self.triplets.append(TableTriplet(
                        source=exercise_name,
                        relation=action,
                        target=part
                    ))
    
    def _extract_exercise_steps(self, text: str):
        """
        提取练习步骤
        格式：练习一
              起始姿势
              ·仰卧；
              ·双腿弯曲；
        """
        # 匹配练习块
        exercise_pattern = r'练习([\u4e00-\u9fff一二三四五六七八九十]+)\s*\n+((?:.*?\n)*?)(?=练习[\u4e00-\u9fff一二三四五六七八九十]+|$)'
        
        for match in re.finditer(exercise_pattern, text, re.MULTILINE | re.DOTALL):
            exercise_num = match.group(1).strip()
            exercise_content = match.group(2)
            exercise_name = f"练习{exercise_num}"
            
            # 提取起始姿势
            posture_pattern = r'起始姿势\s*\n+((?:[·•\-]\s*[^\n]+\s*\n*)+)'
            posture_match = re.search(posture_pattern, exercise_content)
            
            if posture_match:
                postures_text = posture_match.group(1)
                postures = re.findall(r'[·•\-]\s*([^；;。\n]+)', postures_text)
                
                for posture in postures:
                    posture = posture.strip()
                    if posture:
                        self.triplets.append(TableTriplet(
                            source=exercise_name,
                            relation="起始姿势",
                            target=posture
                        ))
            
            # 提取动作要领
            action_pattern = r'动作要领\s*\n+((?:[·•\-]\s*[^\n]+\s*\n*)+)'
            action_match = re.search(action_pattern, exercise_content)
            
            if action_match:
                actions_text = action_match.group(1)
                actions = re.findall(r'[·•\-]\s*([^；;。\n]+)', actions_text)
                
                for action in actions:
                    action = action.strip()
                    if action:
                        self.triplets.append(TableTriplet(
                            source=exercise_name,
                            relation="动作要领",
                            target=action
                        ))
    
    def _extract_action_points(self, text: str):
        """提取动作要领的详细步骤"""
        # 已在 _extract_exercise_steps 中处理
        pass
    
    def _extract_precautions(self, text: str):
        """
        提取注意事项
        格式：注意事项
              ·头部不要离开地面；
        """
        # 匹配练习块
        exercise_pattern = r'练习([\u4e00-\u9fff一二三四五六七八九十]+)\s*\n+((?:.*?\n)*?)(?=练习[\u4e00-\u9fff一二三四五六七八九十]+|$)'
        
        for match in re.finditer(exercise_pattern, text, re.MULTILINE | re.DOTALL):
            exercise_num = match.group(1).strip()
            exercise_content = match.group(2)
            exercise_name = f"练习{exercise_num}"
            
            # 提取注意事项
            precaution_pattern = r'注意事项[：:]*\s*\n*((?:[·•\-]\s*[^\n]+\s*\n*)+)'
            precaution_match = re.search(precaution_pattern, exercise_content)
            
            if precaution_match:
                precautions_text = precaution_match.group(1)
                precautions = re.findall(r'[·•\-]\s*([^；;。\n]+)', precautions_text)
                
                for precaution in precautions:
                    precaution = precaution.strip()
                    if precaution:
                        self.triplets.append(TableTriplet(
                            source=exercise_name,
                            relation="注意事项",
                            target=precaution
                        ))
    
    def _extract_repetitions(self, text: str):
        """
        提取重复次数
        格式：重复次数：3次。
        """
        # 匹配练习块
        exercise_pattern = r'练习([\u4e00-\u9fff一二三四五六七八九十]+)\s*\n+((?:.*?\n)*?)(?=练习[\u4e00-\u9fff一二三四五六七八九十]+|$)'
        
        for match in re.finditer(exercise_pattern, text, re.MULTILINE | re.DOTALL):
            exercise_num = match.group(1).strip()
            exercise_content = match.group(2)
            exercise_name = f"练习{exercise_num}"
            
            # 提取重复次数
            rep_pattern = r'重复次数[：:]\s*([^\n。；;]+)'
            rep_match = re.search(rep_pattern, exercise_content)
            
            if rep_match:
                repetition = rep_match.group(1).strip()
                self.triplets.append(TableTriplet(
                    source=exercise_name,
                    relation="重复次数",
                    target=repetition
                ))


def extract_table_triplets(text: str) -> List[TableTriplet]:
    """便捷函数：从文本中提取表格三元组"""
    extractor = RehabilitationTableExtractor()
    return extractor.extract_from_text(text)


if __name__ == "__main__":
    # 测试
    test_text = """
练习效果
练习	效果
一	·强化腹部和腿部肌肉
·拉伸肩胛带肌群、颈前肌群和颈后肌群
二	·强化腹部、腿部、手臂和肩胛骨肌肉
·拉伸颈前肌群和颈后肌群

练习一

起始姿势
·仰卧；
·双腿弯曲；
·脚跟着地；
·双臂伸直，在身体两侧微微外展；
·掌心贴地。
动作要领
·收紧腹肌；
·下背部向地面下压；
·脚跟向地面下压；
·双手平放于地面，尽量朝脚的方向伸直；
·下巴朝胸部方向内收；
·头部尽可能向上伸展，但不要离地；
·保持这个姿势片刻；
·全身放松。
重复次数：3次。
注意事项
·头部不要离开地面；
·不要压出双下巴；
·保持呼吸。
    """
    
    triplets = extract_table_triplets(test_text)
    
    print(f"提取的三元组数量: {len(triplets)}")
    print("\n三元组列表：")
    for i, triplet in enumerate(triplets, 1):
        print(f"{i}. ({triplet.source}) -[{triplet.relation}]-> ({triplet.target})")

