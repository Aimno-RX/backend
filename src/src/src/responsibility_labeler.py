# -*- coding: utf-8 -*-
"""
句子职责标注器
负责为句子打上职责标签
"""

import re


RESPONSIBILITY_RULES = {
    "动作描述": [
        r"屈伸", r"旋转", r"侧弯", r"耸肩", r"拉伸", r"训练", r"练习", r"锻炼",
        r"动作", r"抬头", r"低头", r"转头", r"摇头", r"点头"
    ],
    "频次描述": [
        r"\d+\s*次", r"\d+\s*组", r"\d+\s*遍", r"\d+\s*回", r"\d+\s*秒", r"\d+\s*分钟",
        r"每天", r"每周", r"每组", r"每日", r"保持\s*\d+\s*秒", r"持续\s*\d+\s*秒"
    ],
    "姿势描述": [
        r"坐姿", r"站姿", r"卧姿", r"仰卧", r"俯卧", r"侧卧", r"跪姿",
        r"双手", r"单手", r"双肩", r"单肩", r"双腿", r"单腿"
    ],
    "效果描述": [
        r"缓解", r"改善", r"增强", r"提高", r"促进", r"恢复", r"预防",
        r"减少", r"消除", r"强化", r"加强"
    ],
    "注意事项": [
        r"注意", r"避免", r"不要", r"禁止", r"切勿", r"不能", r"不可",
        r"小心", r"谨慎", r"保持", r"维持", r"确保"
    ],
    "强度描述": [
        r"轻", r"中", r"重", r"缓慢", r"快速", r"温和", r"剧烈", r"适度",
        r"循序渐进", r"由浅入深", r"由易到难"
    ],
}


def label_sentence_responsibility(sentence: str):
    """
    给单个句子打职责标签
    """
    labels = []

    if not sentence:
        return labels

    for label, patterns in RESPONSIBILITY_RULES.items():
        for pattern in patterns:
            if re.search(pattern, sentence):
                labels.append(label)
                break

    return labels


def label_document_structure(document_structure):
    """
    给整个结构化文档中的所有句子打标签
    """
    for sentence in document_structure.sentences:
        sentence.labels = label_sentence_responsibility(sentence.text)

    return document_structure