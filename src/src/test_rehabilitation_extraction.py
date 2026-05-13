# -*- coding: utf-8 -*-
"""
康复训练三元组提取集成测试脚本
验证所有组件是否正常工作
"""

import sys
import os

# 添加backend目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.insert(0, backend_dir)

import logging

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)


def test_rehabilitation_extractor():
    """测试康复训练提取器"""
    logger.info("\n" + "="*80)
    logger.info("【测试1】康复训练三元组提取器")
    logger.info("="*80)
    
    try:
        from src.rehabilitation_triplet_extractor import extract_rehabilitation_triplets
        
        test_text = """
        颈部屈伸训练：患者坐姿，头部缓慢向前屈曲，停留5秒，然后缓慢后伸，停留5秒。
        做3组，每组10次，每周3次。该训练可增强颈部肌肉力量，缓解颈痛。
        注意不要过度用力，避免颈部受伤。
        """
        
        triplets, entities = extract_rehabilitation_triplets(test_text)
        
        logger.info(f"✅ 提取器工作正常")
        logger.info(f"   提取三元组: {len(triplets)} 个")
        logger.info(f"   提取实体类型: {len(entities)} 种")
        
        if triplets:
            logger.info(f"   示例三元组:")
            for triplet in triplets[:5]:
                logger.info(f"     ({triplet.source}) -[{triplet.relation}]-> ({triplet.target})")
        
        if entities:
            logger.info(f"   提取的实体:")
            for entity_type, entity_set in entities.items():
                if entity_set:
                    logger.info(f"     {entity_type}: {entity_set}")
        
        return len(triplets) > 0
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return False


def test_document_type_detector():
    """测试文档类型检测器"""
    logger.info("\n" + "="*80)
    logger.info("【测试2】文档类型检测器")
    logger.info("="*80)
    
    try:
        from src.triplet_enhancement_integration import DocumentTypeDetector
        
        test_cases = [
            ("颈部屈伸训练：做3组，每组10次，每周3次。", "rehabilitation"),
            ("颈椎病是一种常见疾病，症状包括颈痛和头晕。", "medical"),
            ("这是一个通用文本，没有特定的医学或康复内容。", "general"),
        ]
        
        all_correct = True
        for text, expected_type in test_cases:
            detected_type = DocumentTypeDetector.detect_document_type(text)
            if detected_type == expected_type:
                logger.info(f"✅ 正确识别: {expected_type}")
            else:
                logger.warning(f"⚠️  识别不准确: 期望{expected_type}，实际{detected_type}")
                all_correct = False
        
        return all_correct
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return False


def test_triplet_enhancement_pipeline():
    """测试三元组融合管道"""
    logger.info("\n" + "="*80)
    logger.info("【测试3】三元组融合管道")
    logger.info("="*80)
    
    try:
        from src.triplet_enhancement_integration import TripletEnhancementPipeline, GraphDocument, Node, Relationship
        
        # 创建模拟的LLM提取结果
        node1 = Node(id="颈部屈伸训练", type="康复训练")
        node2 = Node(id="增强肌力", type="效果")
        rel = Relationship(source=node1, target=node2, type="效果")
        
        mock_graph_doc = GraphDocument(
            nodes=[node1, node2],
            relationships=[rel],
            source=None
        )
        
        test_text = """
        颈部屈伸训练：患者坐姿，头部缓慢向前屈曲，停留5秒，然后缓慢后伸，停留5秒。
        做3组，每组10次，每周3次。该训练可增强颈部肌肉力量，缓解颈痛。
        """
        
        pipeline = TripletEnhancementPipeline()
        enhanced_docs = pipeline.enhance_graph_documents(
            [mock_graph_doc],
            test_text,
            doc_type='rehabilitation'
        )
        
        logger.info(f"✅ 融合管道工作正常")
        logger.info(f"   增强后文档数: {len(enhanced_docs)}")
        
        if enhanced_docs:
            doc = enhanced_docs[0]
            logger.info(f"   增强后节点数: {len(doc.nodes)}")
            logger.info(f"   增强后关系数: {len(doc.relationships)}")
            
            stats = pipeline.get_statistics()
            logger.info(f"   统计信息:")
            logger.info(f"     LLM三元组: {stats.get('llm_triplets', 0)}")
            logger.info(f"     规则三元组: {stats.get('rule_triplets', 0)}")
            logger.info(f"     融合后三元组: {stats.get('merged_triplets', 0)}")
            logger.info(f"     去重后三元组: {stats.get('deduplicated_triplets', 0)}")
            
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return False


def test_llm_integration():
    """测试llm.py集成"""
    logger.info("\n" + "="*80)
    logger.info("【测试4】llm.py集成检查")
    logger.info("="*80)
    
    try:
        llm_file = os.path.join(current_dir, 'llm.py')
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
                logger.info(f"✅ {description}")
            else:
                logger.error(f"❌ {description} - 未找到关键字: {keyword}")
                all_found = False
        
        return all_found
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return False


def main():
    """主测试函数"""
    logger.info("\n" + "="*80)
    logger.info("康复训练三元组提取集成测试")
    logger.info("="*80)
    
    results = {
        '康复训练提取器': test_rehabilitation_extractor(),
        '文档类型检测器': test_document_type_detector(),
        '三元组融合管道': test_triplet_enhancement_pipeline(),
        'llm.py集成': test_llm_integration(),
    }
    
    logger.info("\n" + "="*80)
    logger.info("测试结果总结")
    logger.info("="*80)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        logger.info("\n✅ 所有测试都通过了！")
        logger.info("现在请重新上传《颈椎胸椎功能强化训练》文档，应该会看到显著改善。")
        logger.info("\n预期改善:")
        logger.info("  - 实体节点数从 3 增加到 20+ 个")
        logger.info("  - 关系数从 0 增加到 30+ 个")
        logger.info("  - 包含训练动作、身体部位、频次、姿势、效果等多维度信息")
    else:
        logger.info("\n❌ 有些测试失败了，请查看上面的错误信息。")
    
    logger.info("\n" + "="*80)
    
    return all_passed


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"测试脚本执行失败: {e}", exc_info=True)
        sys.exit(1)

