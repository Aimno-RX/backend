# -*- coding: utf-8 -*-
"""
康复训练三元组提取 - 实际使用示例和测试脚本
"""

import logging
from src.advanced_triplet_extraction import extract_rehabilitation_triplets
from src.triplet_enhancement_integration import (
    TripletEnhancementPipeline,
    DetailedExtractionAnalyzer
)

logging.basicConfig(format='%(asctime)s - %(message)s', level='INFO')


# ============================================================================
# 示例1：基础三元组提取
# ============================================================================

def example_basic_extraction():
    """基础三元组提取示例"""
    print("\n" + "="*80)
    print("示例1：基础三元组提取")
    print("="*80)
    
    # 示例文本
    text = """
    颈部屈伸训练：患者坐姿，头部缓慢向前屈曲，停留5秒，然后缓慢后伸，停留5秒。
    做3组，每组10次，每周3次。该训练可增强颈部肌肉力量，缓解颈痛。
    
    肩部耸动训练：两肩同时向上耸动，停留2秒，然后放松。
    做4组，每组15次，强度中等，每周4次。
    
    颈部旋转训练：头部缓慢向左旋转，停留3秒，然后向右旋转。
    做3组，每组12次，每周3次。该训练改善颈部活动度。
    
    注意事项：避免快速转动，保持正确姿态。
    禁忌症：颈椎不稳定患者禁忌快速旋转。
    """
    
    # 提取三元组
    triplets, entities = extract_rehabilitation_triplets(text)
    
    # 输出结果
    print(f"\n【提取结果】")
    print(f"总三元组数: {len(triplets)}")
    print(f"实体类型数: {len(entities)}")
    
    # 按实体类型输出
    print(f"\n【实体分布】")
    for entity_type, entity_set in sorted(entities.items()):
        print(f"  {entity_type}: {len(entity_set)} 个")
        for entity in sorted(list(entity_set))[:5]:
            print(f"    - {entity}")
        if len(entity_set) > 5:
            print(f"    ... 还有 {len(entity_set) - 5} 个")
    
    # 按关系类型输出三元组
    print(f"\n【三元组分布（按关系类型）】")
    relations = {}
    for triplet in triplets:
        rel = triplet.relation
        if rel not in relations:
            relations[rel] = []
        relations[rel].append(triplet)
    
    for rel, triplet_list in sorted(relations.items()):
        print(f"  {rel}: {len(triplet_list)} 个")
        for triplet in triplet_list[:3]:
            print(f"    ({triplet.source}) -[{triplet.relation}]-> ({triplet.target})")
        if len(triplet_list) > 3:
            print(f"    ... 还有 {len(triplet_list) - 3} 个")


# ============================================================================
# 示例2：详细的参数提取
# ============================================================================

def example_parameter_extraction():
    """详细的参数提取示例"""
    print("\n" + "="*80)
    print("示例2：详细的参数提取")
    print("="*80)
    
    text = """
    颈部屈伸训练：
    - 初级阶段：2组，每组8次，轻度强度，每周2次，停留3秒
    - 中级阶段：3组，每组10-12次，中等强度，每周3次，停留5秒，休息30秒
    - 高级阶段：4组，每组15次，重度强度，每周4次，停留8秒，休息1分钟
    """
    
    triplets, entities = extract_rehabilitation_triplets(text)
    
    print(f"\n【参数提取结果】")
    
    # 按参数类型统计
    param_types = ['组数', '次数', '训练强度', '训练频率', '持续时间', '休息时间']
    for param_type in param_types:
        params = entities.get(param_type, set())
        if params:
            print(f"\n{param_type}:")
            for param in sorted(list(params)):
                print(f"  - {param}")
    
    # 显示参数关系
    print(f"\n【参数关系】")
    param_relations = [t for t in triplets if t.target_type in param_types]
    for triplet in param_relations[:15]:
        print(f"  ({triplet.source}) -[{triplet.relation}]-> ({triplet.target})")


# ============================================================================
# 示例3：多维度关系提取
# ============================================================================

def example_multidimensional_extraction():
    """多维度关系提取示例"""
    print("\n" + "="*80)
    print("示例3：多维度关系提取")
    print("="*80)
    
    text = """
    颈部屈伸训练是一种强化训练，属于基础阶段。
    该训练针对颈部肌肉和斜方肌，涉及颈椎和肩关节。
    训练目标是增强肌力和改善柔韧性。
    该训练可缓解颈痛和肩痛。
    适用于亚急性期和慢性期患者。
    颈椎不稳定患者禁忌该训练。
    """
    
    triplets, entities = extract_rehabilitation_triplets(text)
    
    print(f"\n【多维度关系分布】")
    
    # 按源实体类型分组
    source_types = {}
    for triplet in triplets:
        src_type = triplet.source_type
        if src_type not in source_types:
            source_types[src_type] = []
        source_types[src_type].append(triplet)
    
    for src_type in sorted(source_types.keys()):
        triplet_list = source_types[src_type]
        print(f"\n{src_type} 的关系:")
        for triplet in triplet_list:
            print(f"  ({triplet.source}) -[{triplet.relation}]-> ({triplet.target})")


# ============================================================================
# 示例4：禁忌症和注意事项提取
# ============================================================================

def example_contraindication_extraction():
    """禁忌症和注意事项提取示例"""
    print("\n" + "="*80)
    print("示例4：禁忌症和注意事项提取")
    print("="*80)
    
    text = """
    颈部快速旋转训练：
    禁忌症：颈椎不稳定患者禁忌，严重骨质疏松患者禁忌。
    注意事项：应该避免过度用力，需要保持正确姿态，应该循序渐进。
    
    肩部外旋训练：
    避免突然改变头部位置。
    不应该在急性期进行。
    """
    
    triplets, entities = extract_rehabilitation_triplets(text)
    
    print(f"\n【禁忌症】")
    contraindications = entities.get('禁忌症', set())
    for c in sorted(list(contraindications)):
        print(f"  - {c}")
    
    print(f"\n【注意事项】")
    precautions = entities.get('注意事项', set())
    for p in sorted(list(precautions)):
        print(f"  - {p}")
    
    print(f"\n【禁忌症关系】")
    contraindication_relations = [t for t in triplets if t.relation == '禁忌症']
    for triplet in contraindication_relations:
        print(f"  ({triplet.source}) -[{triplet.relation}]-> ({triplet.target})")
    
    print(f"\n【注意事项关系】")
    precaution_relations = [t for t in triplets if t.relation == '注意事项']
    for triplet in precaution_relations:
        print(f"  ({triplet.source}) -[{triplet.relation}]-> ({triplet.target})")


# ============================================================================
# 示例5：生成详细报告
# ============================================================================

def example_detailed_report():
    """生成详细提取报告示例"""
    print("\n" + "="*80)
    print("示例5：生成详细提取报告")
    print("="*80)
    
    text = """
    颈椎胸椎功能强化训练方案
    
    第一阶段：急性期（第1-2周）
    颈部拉伸训练：轻度强度，每天1次，每次3组，每组5次，停留3秒。
    肩部耸动训练：轻度强度，每天1次，每次2组，每组8次。
    
    第二阶段：亚急性期（第3-6周）
    颈部屈伸训练：中等强度，每周3次，每次3组，每组10次，停留5秒。
    肩部外旋训练：中等强度，每周3次，每次3组，每组12次。
    背部拉伸训练：中等强度，每周2次，每次2组，每组10次。
    
    第三阶段：慢性期（第7周以后）
    颈部旋转训练：高强度，每周4次，每次4组，每组15次，停留8秒。
    胸椎强化训练：高强度，每周4次，每次4组，每组15次。
    
    训练目标：增强肌力、改善柔韧性、增加稳定性、改善姿态、缓解疼痛。
    
    禁忌症：颈椎不稳定患者禁忌快速旋转，严重骨质疏松患者禁忌高强度训练。
    注意事项：避免过度用力，保持正确姿态，循序渐进，停止疼痛。
    """
    
    triplets, entities = extract_rehabilitation_triplets(text)
    
    # 生成报告
    report = DetailedExtractionAnalyzer.generate_extraction_report(
        text,
        [],  # 空的LLM三元组（用于演示）
        triplets
    )
    
    print(report)


# ============================================================================
# 示例6：三元组融合演示
# ============================================================================

def example_triplet_fusion():
    """三元组融合演示"""
    print("\n" + "="*80)
    print("示例6：三元组融合演示")
    print("="*80)
    
    text = """
    颈部屈伸训练：做3组，每组10次，每周3次，强度中等。
    该训练可增强颈部肌肉力量，缓解颈痛。
    """
    
    # 模拟LLM提取的三元组
    llm_triplets = [
        {
            'source': '颈部屈伸训练',
            'relation': '属于类型',
            'target': '强化训练',
            'source_type': '训练动作',
            'target_type': '动作类型'
        },
        {
            'source': '颈部屈伸训练',
            'relation': '训练目标',
            'target': '增强肌力',
            'source_type': '训练动作',
            'target_type': '训练目标'
        }
    ]
    
    # 规则提取的三元组
    rule_triplets, entities = extract_rehabilitation_triplets(text)
    
    # 融合
    pipeline = TripletEnhancementPipeline()
    merged = pipeline._merge_triplets(llm_triplets, rule_triplets)
    
    print(f"\n【融合结果】")
    print(f"LLM三元组: {len(llm_triplets)} 个")
    print(f"规则三元组: {len(rule_triplets)} 个")
    print(f"融合后: {len(merged)} 个")
    
    print(f"\n【融合后的三元组】")
    for triplet in merged:
        source_label = triplet.get('source', 'llm')
        confidence = triplet.get('confidence', 0)
        print(f"  ({triplet['source']}) -[{triplet['relation']}]-> ({triplet['target']}) "
              f"[来源: {source_label}, 置信度: {confidence:.2f}]")


# ============================================================================
# 主函数
# ============================================================================

def main():
    """运行所有示例"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "康复训练三元组提取 - 使用示例" + " "*24 + "║")
    print("╚" + "="*78 + "╝")
    
    # 运行所有示例
    example_basic_extraction()
    example_parameter_extraction()
    example_multidimensional_extraction()
    example_contraindication_extraction()
    example_detailed_report()
    example_triplet_fusion()
    
    print("\n" + "="*80)
    print("所有示例执行完毕")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()

