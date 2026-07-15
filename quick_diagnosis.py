# -*- coding: utf-8 -*-
"""
快速诊断脚本 - 检查康复训练提取器是否工作
"""

import sys
import os

# 添加backend目录到Python路径
backend_dir = r"C:\Users\25592\Desktop\llm-graph-builder-main\llm-graph-builder-main\backend"
sys.path.insert(0, backend_dir)

print("="*80)
print("康复训练提取器诊断")
print("="*80)

# 测试1：检查文件是否存在
print("\n【测试1】检查文件是否存在...")
files_to_check = [
    os.path.join(backend_dir, "src", "rehabilitation_triplet_extractor.py"),
    os.path.join(backend_dir, "src", "triplet_enhancement_integration.py"),
    os.path.join(backend_dir, "src", "medical_extraction_config.py"),
    os.path.join(backend_dir, "src", "llm.py"),
]

all_exist = True
for file_path in files_to_check:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)}")
    else:
        print(f"❌ {os.path.basename(file_path)} - 文件不存在")
        all_exist = False

if not all_exist:
    print("\n❌ 有文件缺失，请检查文件是否正确创建")
    sys.exit(1)

# 测试2：测试康复训练提取器
print("\n【测试2】测试康复训练提取器...")
try:
    from src.rehabilitation_triplet_extractor import extract_rehabilitation_triplets
    
    test_text = """
    颈部屈伸训练：患者坐姿，头部缓慢向前屈曲，停留5秒，然后缓慢后伸，停留5秒。
    做3组，每组10次，每周3次。该训练可增强颈部肌肉力量，缓解颈痛。
    """
    
    triplets, entities = extract_rehabilitation_triplets(test_text)
    
    print(f"✅ 提取器工作正常")
    print(f"   提取三元组: {len(triplets)} 个")
    print(f"   提取实体类型: {len([k for k, v in entities.items() if v])} 种")
    
    if triplets:
        print(f"\n   示例三元组:")
        for triplet in triplets[:5]:
            print(f"     ({triplet.source}) -[{triplet.relation}]-> ({triplet.target})")
    
    if len(triplets) == 0:
        print("\n⚠️  警告：没有提取到任何三元组！")
        
except Exception as e:
    print(f"❌ 提取器测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试3：测试文档类型检测
print("\n【测试3】测试文档类型检测...")
try:
    from src.triplet_enhancement_integration import DocumentTypeDetector
    
    test_cases = [
        ("颈部屈伸训练：做3组，每组10次", "rehabilitation"),
        ("颈椎病是一种常见疾病", "medical"),
    ]
    
    for text, expected in test_cases:
        detected = DocumentTypeDetector.detect_document_type(text)
        if detected == expected:
            print(f"✅ 正确识别: {expected}")
        else:
            print(f"⚠️  识别为: {detected}，期望: {expected}")
            
except Exception as e:
    print(f"❌ 文档类型检测失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试4：检查llm.py集成
print("\n【测试4】检查llm.py集成...")
try:
    llm_file = os.path.join(backend_dir, "src", "llm.py")
    with open(llm_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        'TripletEnhancementPipeline': '融合管道导入',
        'DocumentTypeDetector': '文档类型检测器导入',
        "doc_type == 'rehabilitation'": '康复文档检测',
        'enhance_graph_documents': '增强方法调用',
    }
    
    all_found = True
    for keyword, description in checks.items():
        if keyword in content:
            print(f"✅ {description}")
        else:
            print(f"❌ {description} - 未找到")
            all_found = False
    
    if not all_found:
        print("\n⚠️  llm.py可能未正确集成")
        
except Exception as e:
    print(f"❌ llm.py检查失败: {e}")
    sys.exit(1)

print("\n" + "="*80)
print("诊断完成")
print("="*80)
print("\n如果所有测试都通过，请：")
print("1. 重启后端服务")
print("2. 重新上传《颈椎胸椎功能强化训练》文档")
print("3. 查看后端日志，应该看到'检测到康复训练文档'的消息")
print("\n" + "="*80)

