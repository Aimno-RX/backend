# -*- coding: utf-8 -*-
"""
快速测试修复结果
"""

import sys
import os

# 添加路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

print("=" * 80)
print("快速测试修复结果")
print("=" * 80)

# 测试1: 导入修复
print("\n【测试1】测试 GraphDocument 导入...")
try:
    from src.triplet_enhancement_integration import GraphDocument, Node, Relationship
    print("✅ GraphDocument 导入成功")
    print(f"   GraphDocument: {GraphDocument}")
    print(f"   Node: {Node}")
    print(f"   Relationship: {Relationship}")
except Exception as e:
    print(f"❌ 导入失败: {e}")

# 测试2: 文档类型检测
print("\n【测试2】测试文档类型检测...")
try:
    from src.extraction_integration import DocumentTypeDetector
    
    test_cases = [
        ("颈部屈伸训练：做3组，每组10次，每周3次。", "rehabilitation"),
        ("颈椎病是一种常见疾病，症状包括颈痛和头晕。", "medical"),
        ("今天天气很好。", "general"),
    ]
    
    all_passed = True
    for text, expected in test_cases:
        detected = DocumentTypeDetector.detect_document_type(text)
        status = "✅" if detected == expected else "❌"
        print(f"{status} 文本: '{text[:20]}...' -> 期望: {expected}, 实际: {detected}")
        if detected != expected:
            all_passed = False
    
    if all_passed:
        print("✅ 所有文档类型检测测试通过")
    else:
        print("⚠️  部分测试未通过")
        
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

# 测试3: 融合管道
print("\n【测试3】测试融合管道...")
try:
    from src.triplet_enhancement_integration import TripletEnhancementPipeline, GraphDocument, Node, Relationship
    
    # 创建测试数据
    node1 = Node(id="颈部屈伸", type="训练动作")
    node2 = Node(id="颈部肌肉", type="肌肉群")
    rel = Relationship(source=node1, target=node2, type="针对肌肉")
    
    graph_doc = GraphDocument(
        nodes=[node1, node2],
        relationships=[rel],
        source=None
    )
    
    test_text = "颈部屈伸训练：做3组，每组10次，针对颈部肌肉。"
    
    pipeline = TripletEnhancementPipeline()
    enhanced = pipeline.enhance_graph_documents([graph_doc], test_text, 'rehabilitation')
    
    print(f"✅ 融合管道工作正常")
    print(f"   增强后文档数: {len(enhanced)}")
    
    stats = pipeline.get_statistics()
    print(f"   统计信息:")
    print(f"     LLM三元组: {stats.get('llm_triplets', 0)}")
    print(f"     规则三元组: {stats.get('rule_triplets', 0)}")
    print(f"     融合后三元组: {stats.get('merged_triplets', 0)}")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)

