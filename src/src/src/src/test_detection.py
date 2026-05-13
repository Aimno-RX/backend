# -*- coding: utf-8 -*-
"""测试文档类型检测"""

import sys
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from src.extraction_integration import DocumentTypeDetector

# 测试文本
test_text = "颈部屈伸训练：做3组，每组10次，每周3次。"

# 关键词列表
rehabilitation_keywords = [
    '训练', '康复', '强化', '拉伸', '屈伸', '旋转',
    '组数', '次数', '频率', '强度', '阶段',
    '功能改善', '症状缓解', '预防', '恢复',
    '颈椎', '胸椎', '肌肉', '关节', '姿态'
]

# 计算匹配
matched = [k for k in rehabilitation_keywords if k in test_text]
score = len(matched)

print(f"测试文本: {test_text}")
print(f"匹配关键词数: {score}")
print(f"匹配的关键词: {matched}")
print(f"检测结果: {DocumentTypeDetector.detect_document_type(test_text)}")

