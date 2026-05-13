# -*- coding: utf-8 -*-
"""
三元组提取诊断脚本
用于诊断为什么知识图谱没有改善
"""

import logging
import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    handlers=[
        logging.FileHandler('/c:/Users/25592/Desktop/llm-graph-builder-main/llm-graph-builder-main/triplet_diagnosis.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def diagnose_triplet_extraction():
    """诊断三元组提取问题"""
    
    logger.info("="*80)
    logger.info("开始诊断三元组提取问题")
    logger.info("="*80)
    
    # 步骤1：检查文件是否存在
    logger.info("\n【步骤1】检查必要文件是否存在...")
    required_files = [
        '/c:/Users/25592/Desktop/llm-graph-builder-main/llm-graph-builder-main/backend/src/advanced_triplet_extraction.py',
        '/c:/Users/25592/Desktop/llm-graph-builder-main/llm-graph-builder-main/backend/src/triplet_enhancement_integration.py',
        '/c:/Users/25592/Desktop/llm-graph-builder-main/llm-graph-builder-main/backend/src/triplet_extraction_examples.py',
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            logger.info(f"✅ 文件存在: {file_path}")
        else:
            logger.error(f"❌ 文件缺失: {file_path}")
    
    # 步骤2：测试高级提取器
    logger.info("\n【步骤2】测试高级三元组提取器...")
    try:
        from src.advanced_triplet_extraction import extract_rehabilitation_triplets
        
        test_text = """
        颈部屈伸训练：患者坐姿，头部缓慢向前屈曲，停留5秒，然后缓慢后伸，停留5秒。
        做3组，每组10次，每周3次。该训练可增强颈部肌肉力量，缓解颈痛。
        """
        
        triplets, entities = extract_rehabilitation_triplets(test_text)
        
        logger.info(f"✅ 高级提取器工作正常")
        logger.info(f"   提取三元组: {len(triplets)} 个")
        logger.info(f"   提取实体类型: {len(entities)} 种")
        
        if len(triplets) > 0:
            logger.info(f"   示例三元组:")
            for triplet in triplets[:5]:
                logger.info(f"     ({triplet.source}) -[{triplet.relation}]-> ({triplet.target})")
        else:
            logger.warning("❌ 没有提取到任何三元组！")
            
    except Exception as e:
        logger.error(f"❌ 高级提取器测试失败: {e}", exc_info=True)
    
    # 步骤3：测试融合管道
    logger.info("\n【步骤3】测试三元组融合管道...")
    try:
        from src.triplet_enhancement_integration import TripletEnhancementPipeline
        from langchain_core.graph_document import GraphDocument, Node, Relationship
        
        # 创建模拟的LLM提取结果
        node1 = Node(id="颈部屈伸训练", type="训练动作")
        node2 = Node(id="增强肌力", type="训练目标")
        rel = Relationship(source=node1, target=node2, type="训练目标")
        
        mock_graph_doc = GraphDocument(
            nodes=[node1, node2],
            relationships=[rel]
        )
        
        test_text = "颈部屈伸训练：做3组，每组10次，每周3次。"
        
        pipeline = TripletEnhancementPipeline()
        enhanced_docs = pipeline.enhance_graph_documents(
            [mock_graph_doc],
            test_text,
            doc_type='rehabilitation'
        )
        
        logger.info(f"✅ 融合管道工作正常")
        logger.info(f"   增强后文档数: {len(enhanced_docs)}")
        
        if enhanced_docs:
            stats = pipeline.get_statistics()
            logger.info(f"   统计信息:")
            logger.info(f"     LLM三元组: {stats.get('llm_triplets', 0)}")
            logger.info(f"     规则三元组: {stats.get('rule_triplets', 0)}")
            logger.info(f"     融合后三元组: {stats.get('merged_triplets', 0)}")
        
    except Exception as e:
        logger.error(f"❌ 融合管道测试失败: {e}", exc_info=True)
    
    # 步骤4：检查文档类型检测
    logger.info("\n【步骤4】检查文档类型检测...")
    try:
        from src.extraction_integration import DocumentTypeDetector
        
        test_texts = [
            ("颈部屈伸训练：做3组，每组10次，每周3次。", "康复训练"),
            ("颈椎病是一种常见疾病，症状包括颈痛和头晕。", "医学"),
            ("这是一个通用文本。", "通用"),
        ]
        
        for text, expected_type in test_texts:
            detected_type = DocumentTypeDetector.detect_document_type(text)
            if detected_type == expected_type or (expected_type == "康复训练" and detected_type == "rehabilitation"):
                logger.info(f"✅ 正确识别: {expected_type} -> {detected_type}")
            else:
                logger.warning(f"⚠️  识别不准确: 期望{expected_type}，实际{detected_type}")
    
    except Exception as e:
        logger.error(f"❌ 文档类型检测测试失败: {e}", exc_info=True)
    
    # 步骤5：检查llm.py是否正确集成
    logger.info("\n【步骤5】检查llm.py集成...")
    try:
        with open('/c:/Users/25592/Desktop/llm-graph-builder-main/llm-graph-builder-main/backend/src/llm.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'integrate_advanced_extraction' in content:
            logger.info("✅ llm.py已集成高级提取器")
        else:
            logger.error("❌ llm.py未集成高级提取器")
            
        if 'triplet_enhancement_integration' in content:
            logger.info("✅ llm.py已导入融合管道")
        else:
            logger.error("❌ llm.py未导入融合管道")
            
    except Exception as e:
        logger.error(f"❌ 检查llm.py失败: {e}", exc_info=True)
    
    # 步骤6：检查extraction_integration.py
    logger.info("\n【步骤6】检查extraction_integration.py...")
    try:
        with open('/c:/Users/25592/Desktop/llm-graph-builder-main/llm-graph-builder-main/backend/src/extraction_integration.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'rehab_score > 3' in content or 'rehab_score > 5' in content:
            logger.info("✅ extraction_integration.py已配置")
        else:
            logger.warning("⚠️  extraction_integration.py可能需要调整")
            
    except Exception as e:
        logger.error(f"❌ 检查extraction_integration.py失败: {e}", exc_info=True)
    
    logger.info("\n" + "="*80)
    logger.info("诊断完成")
    logger.info("="*80)


def test_with_real_document():
    """使用真实文档测试"""
    logger.info("\n" + "="*80)
    logger.info("使用真实文档测试")
    logger.info("="*80)
    
    try:
        # 读取真实文档的前5000个字符
        doc_path = '/c:/Users/25592/Desktop/llm-graph-builder-main/llm-graph-builder-main/test/《颈椎胸椎功能强化训练》已整理完毕.docx'
        
        if not os.path.exists(doc_path):
            logger.error(f"❌ 文档不存在: {doc_path}")
            return
        
        # 尝试读取docx文件
        try:
            from docx import Document as DocxDocument
            doc = DocxDocument(doc_path)
            text = '\n'.join([para.text for para in doc.paragraphs[:100]])
        except:
            logger.warning("⚠️  无法读取docx文件，尝试使用文本提取")
            text = ""
        
        if text:
            logger.info(f"文档内容长度: {len(text)} 字符")
            logger.info(f"文档前500字符:\n{text[:500]}")
            
            # 测试提取
            from src.advanced_triplet_extraction import extract_rehabilitation_triplets
            triplets, entities = extract_rehabilitation_triplets(text)
            
            logger.info(f"\n提取结果:")
            logger.info(f"  三元组数: {len(triplets)}")
            logger.info(f"  实体类型: {len(entities)}")
            
            if triplets:
                logger.info(f"  示例三元组:")
                for triplet in triplets[:10]:
                    logger.info(f"    ({triplet.source}) -[{triplet.relation}]-> ({triplet.target})")
        
    except Exception as e:
        logger.error(f"❌ 真实文档测试失败: {e}", exc_info=True)


if __name__ == "__main__":
    diagnose_triplet_extraction()
    test_with_real_document()
    
    logger.info("\n诊断日志已保存到: /c:/Users/25592/Desktop/llm-graph-builder-main/llm-graph-builder-main/triplet_diagnosis.log")

