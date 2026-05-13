import logging
from langchain_core.documents import Document
import os
from langchain_openai import ChatOpenAI
from langchain_experimental.graph_transformers import LLMGraphTransformer
from src.shared.constants import ADDITIONAL_INSTRUCTIONS
from src.shared.llm_graph_builder_exception import LLMGraphBuilderException
import re
from typing import List
from langchain_core.callbacks.manager import CallbackManager
from src.shared.common_fn import UniversalTokenUsageHandler,get_value_from_env

def get_llm(model: str):
    """Retrieve the specified language model based on the model name.
    优化版本：只支持DeepSeek模型，用于医学知识图谱构建
    """
    model = model.upper().replace('.', '_').replace(' ', '_').strip()
    env_key = f"LLM_MODEL_CONFIG_{model}"
    env_value = get_value_from_env(env_key)

    if not env_value:
        err = f"Environment variable '{env_key}' is not defined as per format or missing"
        logging.error(err)
        raise Exception(err)
    
    logging.info("Model: {}".format(env_key))
    callback_handler = UniversalTokenUsageHandler()
    callback_manager = CallbackManager([callback_handler])
    
    try:
        # DeepSeek模型配置（通过OpenAI兼容接口）
        # 格式：model_name, api_endpoint, api_key
        model_name, api_endpoint, api_key = env_value.split(",")
        llm = ChatOpenAI(
            api_key=api_key,
            base_url=api_endpoint,
            model=model_name,
            temperature=0,
            callbacks=callback_manager,
            max_tokens=4096,  # 大幅增加输出token，确保完整提取所有实体
            request_timeout=180,  # 增加超时时间，适合大文件处理
        )
        logging.info(f"DeepSeek模型已创建 - 模型版本: {model_name}")
        
    except Exception as e:
        err = f"Error while creating DeepSeek LLM '{model}': {str(e)}"
        logging.error(err)
        raise Exception(err)
 
    logging.info(f"Model created - Model Version: {model}")
    return llm, model_name, callback_handler

def get_llm_model_name(llm):
    """Extract name of llm model from llm object"""
    for attr in ["model_name", "model", "model_id"]:
        model_name = getattr(llm, attr, None)
        if model_name:
            return model_name.lower()
    logging.info("Could not determine model name; defaulting to empty string")
    return ""

def get_combined_chunks(chunkId_chunkDoc_list, chunks_to_combine):
    combined_chunk_document_list = []
    combined_chunks_page_content = [
        "\n\n".join(
            document["chunk_doc"].page_content
            for document in chunkId_chunkDoc_list[i : i + chunks_to_combine]
        )
        for i in range(0, len(chunkId_chunkDoc_list), chunks_to_combine)
    ]
    combined_chunks_ids = [
        [
            document["chunk_id"]
            for document in chunkId_chunkDoc_list[i : i + chunks_to_combine]
        ]
        for i in range(0, len(chunkId_chunkDoc_list), chunks_to_combine)
    ]

    for i in range(len(combined_chunks_page_content)):
        combined_chunk_document_list.append(
            Document(
                page_content=combined_chunks_page_content[i],
                metadata={"combined_chunk_ids": combined_chunks_ids[i]},
            )
        )
    return combined_chunk_document_list

def get_chunk_id_as_doc_metadata(chunkId_chunkDoc_list):
    combined_chunk_document_list = [
       Document(
           page_content=document["chunk_doc"].page_content,
           metadata={"chunk_id": [document["chunk_id"]]},
       )
       for document in chunkId_chunkDoc_list
   ]
    return combined_chunk_document_list
      

async def get_graph_document_list(
    llm, combined_chunk_document_list, allowedNodes, allowedRelationship,callback_handler, additional_instructions=None
):
    """
    从文档中提取图结构数据（优化版：专注医学实体提取，过滤空内容）
    """
    if additional_instructions:
        additional_instructions = sanitize_additional_instruction(additional_instructions)
    
    # ================== 增强：中文医学专业提取规则 ==================
    from src.medical_extraction_config import CHINESE_MEDICAL_EXTRACTION_PROMPT, filter_empty_chunks
    
    medical_focus_instructions = CHINESE_MEDICAL_EXTRACTION_PROMPT

    # 医学中文提示词必须放在最前面，确保LLM优先遵循中文提取规则
    if additional_instructions:
        additional_instructions = medical_focus_instructions + "\n\n" + additional_instructions
    else:
        additional_instructions = medical_focus_instructions
    # ================== 新增结束 ==================
    
    # ================== 新增：预过滤空chunk ==================
    original_count = len(combined_chunk_document_list)
    combined_chunk_document_list = filter_empty_chunks(combined_chunk_document_list)
    filtered_count = len(combined_chunk_document_list)
    
    if filtered_count < original_count:
        logging.info(f"过滤空chunk: {original_count} -> {filtered_count} (减少 {original_count - filtered_count} 个)")
    
    if filtered_count == 0:
        logging.warning("所有chunk都被过滤，没有有效内容可提取")
        return [], 0
    # ================== 过滤结束 ==================
    
    graph_document_list = []
    token_usage = 0
    
    try:
        # DeepSeek使用ChatOpenAI接口，支持标准的LLMGraphTransformer
        llm_transformer = LLMGraphTransformer(
            llm=llm,
            node_properties=False,
            relationship_properties=False,
            allowed_nodes=allowedNodes,
            allowed_relationships=allowedRelationship,
            ignore_tool_usage=True,
            additional_instructions=additional_instructions if additional_instructions else ADDITIONAL_INSTRUCTIONS
        )
        
        # 异步转换文档为图结构
        graph_document_list = await llm_transformer.aconvert_to_graph_documents(combined_chunk_document_list)
        
        # ================== 新增：后处理过滤空实体的图文档 ==================
        original_graph_count = len(graph_document_list)
        graph_document_list = [doc for doc in graph_document_list if doc.nodes or doc.relationships]
        filtered_graph_count = len(graph_document_list)
        
        if filtered_graph_count < original_graph_count:
            logging.info(f"过滤空图文档: {original_graph_count} -> {filtered_graph_count} (减少 {original_graph_count - filtered_graph_count} 个)")
        # ================== 过滤结束 ==================
        
        logging.info(f"成功提取 {len(graph_document_list)} 个图文档")
        
    except Exception as e:
       logging.error(f"Error in graph transformation: {e}", exc_info=True)
       raise LLMGraphBuilderException(f"Graph transformation failed: {str(e)}")
    finally:
        try:
            if callback_handler:
                usage = callback_handler.report()
                token_usage = usage.get("total_tokens", 0)
                logging.info(f"本次提取使用Token: {token_usage}")
        except Exception as usage_err:
            logging.error(f"Error while reporting token usage: {usage_err}")

    return graph_document_list, token_usage

async def get_graph_from_llm(model, chunkId_chunkDoc_list, allowedNodes, allowedRelationship, chunks_to_combine, additional_instructions=None):
   try:
       llm, model_name, callback_handler = get_llm(model)
       logging.info(f"Using model: {model_name}")

       chunks_to_combine = max(1, chunks_to_combine or 1)
       combined_chunk_document_list = get_combined_chunks(chunkId_chunkDoc_list, chunks_to_combine)
       logging.info(f"Combined {len(combined_chunk_document_list)} chunks")

       # 兼容未配置 Graph Schema 的情况
       if allowedNodes and str(allowedNodes).strip():
           allowed_nodes = [node.strip() for node in str(allowedNodes).split(',') if node.strip()]
           logging.info(f"Allowed nodes: {allowed_nodes}")
       else:
           allowed_nodes = []
           logging.info("No allowed nodes provided, using unrestricted node extraction")

       allowed_relationships = []
       if allowedRelationship and str(allowedRelationship).strip():
           items = [item.strip() for item in str(allowedRelationship).split(',') if item.strip()]
           if len(items) % 3 != 0:
               raise LLMGraphBuilderException("allowedRelationship must be a multiple of 3 (source, relationship, target)")
           for i in range(0, len(items), 3):
               source, relation, target = items[i:i + 3]
               allowed_relationships.append((source, relation, target))
           logging.info(f"Allowed relationships: {allowed_relationships}")
       else:
           logging.info("No allowed relationships provided, using unrestricted relationship extraction")

       graph_document_list, token_usage = await get_graph_document_list(
           llm,
           combined_chunk_document_list,
           allowed_nodes if allowed_nodes else None,
           allowed_relationships if allowed_relationships else None,
           callback_handler,
           additional_instructions,
       )
       logging.info(f"Generated {len(graph_document_list)} graph documents")
       return graph_document_list, token_usage
   except Exception as e:
       logging.error(f"Error in get_graph_from_llm: {e}", exc_info=True)
       raise LLMGraphBuilderException(f"Error in getting graph from llm: {e}")

def sanitize_additional_instruction(instruction: str) -> str:
   """
   Sanitizes additional instruction by:
   - Replacing curly braces `{}` with `[]` to prevent variable interpretation.
   - Removing potential injection patterns like `os.getenv()`, `eval()`, `exec()`.
   - Stripping problematic special characters.
   - Normalizing whitespace.
   Args:
       instruction (str): Raw additional instruction input.
   Returns:
       str: Sanitized instruction safe for LLM processing.
   """
   logging.info("Sanitizing additional instructions")
   instruction = instruction.replace("{", "[").replace("}", "]")  # Convert `{}` to `[]` for safety
   # Step 2: Block dangerous function calls
   injection_patterns = [r"os\.getenv\(", r"eval\(", r"exec\(", r"subprocess\.", r"import os", r"import subprocess"]
   for pattern in injection_patterns:
       instruction = re.sub(pattern, "[BLOCKED]", instruction, flags=re.IGNORECASE)
   # Step 4: Normalize spaces
   instruction = re.sub(r'\s+', ' ', instruction).strip()
   return instruction
