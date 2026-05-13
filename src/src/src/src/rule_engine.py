# -*- coding: utf-8 -*-
"""
规则引擎
把 document_structure 交给康复训练规则提取器，输出规则三元组
"""

from src.rehabilitation_triplet_extractor import RehabilitationTripletExtractor


def extract_triplets_by_rules(document_structure):
    """
    从结构化文档中抽取规则三元组
    """
    extractor = RehabilitationTripletExtractor()
    triplets, entities = extractor.extract_triplets_from_sentence_units(document_structure.sentences)
    return triplets, entities