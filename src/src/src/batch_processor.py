# -*- coding: utf-8 -*-
"""
批处理优化模块
用于处理大型医学文档（支持1GB以内）
"""

import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
from langchain_core.documents import Document
from src.medical_extraction_config import BATCH_PROCESSING_CONFIG

logging.basicConfig(format='%(asctime)s - %(message)s', level='INFO')


class MedicalBatchProcessor:
    """
    医学文档批处理器
    支持大文件分批处理，提高实体提取效率和准确性
    """
    
    def __init__(self, max_workers=None):
        """
        初始化批处理器
        
        Args:
            max_workers: 最大并行工作线程数，默认使用配置文件中的值
        """
        self.max_workers = max_workers or BATCH_PROCESSING_CONFIG.get("max_workers", 4)
        self.batch_size = BATCH_PROCESSING_CONFIG.get("batch_size", 10)
        self.enable_parallel = BATCH_PROCESSING_CONFIG.get("enable_parallel_processing", True)
        
    def split_into_batches(self, items: List[Any], batch_size: int = None) -> List[List[Any]]:
        """
        将列表分割成批次
        
        Args:
            items: 要分割的项目列表
            batch_size: 每批的大小，默认使用配置值
            
        Returns:
            批次列表
        """
        if batch_size is None:
            batch_size = self.batch_size
            
        batches = []
        for i in range(0, len(items), batch_size):
            batches.append(items[i:i + batch_size])
        
        logging.info(f"分割成 {len(batches)} 个批次，每批最多 {batch_size} 项")
        return batches
    
    async def process_batch_async(self, batch: List[Any], process_func, *args, **kwargs) -> List[Any]:
        """
        异步处理单个批次
        
        Args:
            batch: 要处理的批次
            process_func: 处理函数
            *args, **kwargs: 传递给处理函数的参数
            
        Returns:
            处理结果列表
        """
        results = []
        for item in batch:
            try:
                result = await process_func(item, *args, **kwargs)
                results.append(result)
            except Exception as e:
                logging.error(f"处理项目时出错: {e}")
                results.append(None)
        return results
    
    async def process_all_batches_async(self, items: List[Any], process_func, *args, **kwargs) -> List[Any]:
        """
        异步处理所有批次
        
        Args:
            items: 要处理的所有项目
            process_func: 处理函数
            *args, **kwargs: 传递给处理函数的参数
            
        Returns:
            所有处理结果的扁平列表
        """
        batches = self.split_into_batches(items)
        all_results = []
        
        if self.enable_parallel and len(batches) > 1:
            logging.info(f"启用并行处理，最大工作线程数: {self.max_workers}")
            # 并行处理多个批次
            tasks = [
                self.process_batch_async(batch, process_func, *args, **kwargs)
                for batch in batches
            ]
            batch_results = await asyncio.gather(*tasks)
            for results in batch_results:
                all_results.extend([r for r in results if r is not None])
        else:
            logging.info("使用顺序处理")
            # 顺序处理
            for i, batch in enumerate(batches):
                logging.info(f"处理批次 {i+1}/{len(batches)}")
                results = await self.process_batch_async(batch, process_func, *args, **kwargs)
                all_results.extend([r for r in results if r is not None])
        
        logging.info(f"批处理完成，共处理 {len(all_results)} 项")
        return all_results
    
    def optimize_chunk_size_for_medical_text(self, text: str, base_chunk_size: int = 2000) -> int:
        """
        根据医学文本特征优化分块大小
        
        Args:
            text: 输入文本
            base_chunk_size: 基础分块大小
            
        Returns:
            优化后的分块大小
        """
        # 检测医学术语密度
        medical_keywords = [
            '疾病', '症状', '治疗', '诊断', '病因', '药物', '手术', 
            '检查', '康复', '预后', '并发症', '病理', '解剖'
        ]
        
        keyword_count = sum(text.count(keyword) for keyword in medical_keywords)
        text_length = len(text)
        
        if text_length == 0:
            return base_chunk_size
        
        # 医学术语密度
        density = keyword_count / (text_length / 100)
        
        # 根据密度调整分块大小
        if density > 5:  # 高密度医学文本
            optimized_size = int(base_chunk_size * 1.5)
            logging.info(f"检测到高密度医学文本，增大分块至 {optimized_size}")
        elif density > 2:  # 中等密度
            optimized_size = base_chunk_size
        else:  # 低密度
            optimized_size = int(base_chunk_size * 0.8)
            logging.info(f"检测到低密度医学文本，减小分块至 {optimized_size}")
        
        return optimized_size
    
    def merge_overlapping_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        合并重叠的实体（去重）
        
        Args:
            entities: 实体列表
            
        Returns:
            去重后的实体列表
        """
        from src.medical_extraction_config import ENTITY_MERGE_CONFIG
        
        if not entities:
            return []
        
        # 使用字典去重，key为实体ID
        unique_entities = {}
        
        for entity in entities:
            entity_id = entity.get('id') or entity.get('name')
            if entity_id:
                if entity_id not in unique_entities:
                    unique_entities[entity_id] = entity
                else:
                    # 合并属性
                    existing = unique_entities[entity_id]
                    for key, value in entity.items():
                        if key not in existing or not existing[key]:
                            existing[key] = value
        
        merged_list = list(unique_entities.values())
        logging.info(f"实体去重：{len(entities)} -> {len(merged_list)}")
        return merged_list
    
    def validate_medical_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        验证医学实体的有效性
        
        Args:
            entities: 实体列表
            
        Returns:
            验证后的实体列表
        """
        from src.medical_extraction_config import MEDICAL_ENTITY_TYPES
        
        valid_entities = []
        
        for entity in entities:
            entity_type = entity.get('type') or entity.get('label')
            entity_name = entity.get('id') or entity.get('name')
            
            # 检查实体类型是否有效
            if entity_type not in MEDICAL_ENTITY_TYPES:
                logging.warning(f"无效的实体类型: {entity_type}，实体: {entity_name}")
                continue
            
            # 检查实体名称是否为空
            if not entity_name or len(str(entity_name).strip()) == 0:
                logging.warning(f"实体名称为空，类型: {entity_type}")
                continue
            
            # 检查实体名称长度
            if len(str(entity_name)) > 100:
                logging.warning(f"实体名称过长: {entity_name[:50]}...")
                continue
            
            valid_entities.append(entity)
        
        logging.info(f"实体验证：{len(entities)} -> {len(valid_entities)}")
        return valid_entities
    
    def enhance_chunk_context(self, chunks: List[Document], window_size: int = 1) -> List[Document]:
        """
        增强chunk的上下文信息
        在每个chunk中添加前后chunk的部分内容
        
        Args:
            chunks: 文档chunk列表
            window_size: 上下文窗口大小
            
        Returns:
            增强后的chunk列表
        """
        enhanced_chunks = []
        
        for i, chunk in enumerate(chunks):
            context_before = ""
            context_after = ""
            
            # 添加前文
            if i > 0 and window_size > 0:
                prev_chunks = chunks[max(0, i-window_size):i]
                context_before = " ".join([c.page_content[-200:] for c in prev_chunks])
            
            # 添加后文
            if i < len(chunks) - 1 and window_size > 0:
                next_chunks = chunks[i+1:min(len(chunks), i+1+window_size)]
                context_after = " ".join([c.page_content[:200] for c in next_chunks])
            
            # 创建增强的chunk
            enhanced_content = chunk.page_content
            if context_before:
                enhanced_content = f"[上文]...{context_before}...[/上文]\n\n{enhanced_content}"
            if context_after:
                enhanced_content = f"{enhanced_content}\n\n[下文]...{context_after}...[/下文]"
            
            enhanced_chunk = Document(
                page_content=enhanced_content,
                metadata={**chunk.metadata, "original_content": chunk.page_content}
            )
            enhanced_chunks.append(enhanced_chunk)
        
        logging.info(f"增强了 {len(enhanced_chunks)} 个chunk的上下文")
        return enhanced_chunks


def create_medical_batch_processor(max_workers: int = None) -> MedicalBatchProcessor:
    """
    创建医学批处理器实例
    
    Args:
        max_workers: 最大工作线程数
        
    Returns:
        MedicalBatchProcessor实例
    """
    return MedicalBatchProcessor(max_workers=max_workers)

