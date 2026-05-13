# -*- coding: utf-8 -*-
"""
三元组提取诊断脚本 - Windows版本
用于诊断为什么知识图谱没有改善
"""

import logging
import sys
import os

# 获取当前脚本所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)

# 添加backend目录到Python路径
sys.path.insert(0, backend_dir)

# 配置日志 - 使用相对路径
log_file = os.path.join(project_root, 'triplet_diagnosis.log')

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def check_files():
    """检查必要文件是否存在"""
    logger.info("\n【步骤1】检查必要文件是否存在...")
    logger.info("="*80)
    
    required_files = {
        'advanced_triplet_extraction.py': os.path.join(current_dir, 'advanced_triplet_extraction.py'),
        'triplet_enhancement_integration.py': os.path.join(current_dir, 'triplet_enhancement_integration.py'),
        'triplet_extraction_examples.py': os.path.join(current_dir, 'triplet_extraction_examples.py'),
        'llm.py': os.path.join(current_dir, 'llm.py'),
    }
    
    all_exist = True
    for name, path in required_files.items():
        if os.path.exists(path):
            logger.info(f"✅ {name}")
        else:
            logger.error(f"❌ {name} - 文件缺失: {path}")
            all_exist = False
    
    return all_exist


def test_advanced_extractor():
    """测试高级三元组提取器"""
    logger.info("\n【步骤2】测试高级三元组提取器...")
    logger.info("="*80)
    
    try:
        # 从backend目录导入
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
            return True
        else:
            logger.warning("❌ 没有提取到任何三元组！")
            return False
            
    except Exception as e:
        logger.error(f"❌ 高级提取器测试失败: {e}", exc_info=True)
        return False


def test_fusion_pipeline():
    """测试三元组融合管道"""
    logger.info("\n【步骤3】测试三元组融合管道...")
    logger.info("="*80)
    
    try:
        from src.triplet_enhancement_integration import TripletEnhancementPipeline, GraphDocument, Node, Relationship
        from langchain_core.documents import Document
        
        # 创建模拟的LLM提取结果
        node1 = Node(id="颈部屈伸训练", type="训练动作")
        node2 = Node(id="增强肌力", type="训练目标")
        rel = Relationship(source=node1, target=node2, type="训练目标")
        
        # 创建源文档
        source_doc = Document(page_content="颈部屈伸训练：做3组，每组10次，每周3次。")
        
        mock_graph_doc = GraphDocument(
            nodes=[node1, node2],
            relationships=[rel],
            source=source_doc
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
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ 融合管道测试失败: {e}", exc_info=True)
        return False


def test_document_type_detection():
    """检查文档类型检测"""
    logger.info("\n【步骤4】检查文档类型检测...")
    logger.info("="*80)
    
    try:
        from src.extraction_integration import DocumentTypeDetector
        
        test_texts = [
            ("颈部屈伸训练：做3组，每组10次，每周3次。", "rehabilitation"),
            ("颈椎病是一种常见疾病，症状包括颈痛和头晕。", "medical"),
        ]
        
        all_correct = True
        for text, expected_type in test_texts:
            detected_type = DocumentTypeDetector.detect_document_type(text)
            if detected_type == expected_type:
                logger.info(f"✅ 正确识别: {expected_type}")
            else:
                logger.warning(f"⚠️  识别不准确: 期望{expected_type}，实际{detected_type}")
                all_correct = False
        
        return all_correct
        
    except Exception as e:
        logger.error(f"❌ 文档类型检测测试失败: {e}", exc_info=True)
        return False


def check_llm_integration():
    """检查llm.py是否正确集成"""
    logger.info("\n【步骤5】检查llm.py集成...")
    logger.info("="*80)
    
    try:
        llm_file = os.path.join(current_dir, 'llm.py')
        with open(llm_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = {
            'integrate_advanced_extraction': '高级提取器集成',
            'triplet_enhancement_integration': '融合管道导入',
            'doc_type == \'rehabilitation\'': '康复文档检测',
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
        logger.error(f"❌ 检查llm.py失败: {e}", exc_info=True)
        return False


def main():
    """主诊断函数"""
    logger.info("\n" + "="*80)
    logger.info("开始诊断三元组提取问题")
    logger.info("="*80)
    logger.info(f"项目路径: {project_root}")
    logger.info(f"Backend路径: {backend_dir}")
    logger.info(f"当前脚本路径: {current_dir}")
    
    results = {
        '文件检查': check_files(),
        '高级提取器': test_advanced_extractor(),
        '融合管道': test_fusion_pipeline(),
        '文档类型检测': test_document_type_detection(),
        'llm.py集成': check_llm_integration(),
    }
    
    logger.info("\n" + "="*80)
    logger.info("诊断结果总结")
    logger.info("="*80)
    
    for check_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{check_name}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        logger.info("\n✅ 所有诊断检查都通过了！")
        logger.info("现在请重新上传文档，应该会看到显著改善。")
    else:
        logger.info("\n❌ 有些检查失败了，请查看上面的错误信息。")
        logger.info("常见问题:")
        logger.info("  1. 文件缺失 - 需要复制高级提取器文件")
        logger.info("  2. 导入错误 - 检查依赖是否安装")
        logger.info("  3. llm.py未集成 - 需要手动修改llm.py")
    
    logger.info("\n" + "="*80)
    logger.info(f"诊断日志已保存到: {log_file}")
    logger.info("="*80)
    
    return all_passed


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"诊断脚本执行失败: {e}", exc_info=True)
        sys.exit(1)
