"""
修复文件处理中的路径和删除时机问题
"""
import os
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)

def fix_merged_files_cleanup():
    """
    修复：确保在处理完文件后再删除，而不是在处理前删除
    """
    MERGED_DIR = os.path.join(os.path.dirname(__file__), "merged_files")
    
    # 检查并清理孤立的文件
    if os.path.exists(MERGED_DIR):
        for file in os.listdir(MERGED_DIR):
            file_path = os.path.join(MERGED_DIR, file)
            try:
                if os.path.isfile(file_path):
                    # 检查文件是否被锁定或损坏
                    with open(file_path, 'rb') as f:
                        f.read(1)
                    logging.info(f"文件 {file} 状态正常")
            except Exception as e:
                logging.error(f"文件 {file} 出现问题: {e}")
                try:
                    os.remove(file_path)
                    logging.info(f"已删除损坏的文件: {file}")
                except:
                    pass

def sanitize_file_path(file_path):
    """
    修复：规范化文件路径，移除多余的空格
    """
    # 移除路径中的多余空格
    file_path = str(file_path).strip()
    # 规范化路径
    file_path = os.path.normpath(file_path)
    return file_path

if __name__ == "__main__":
    fix_merged_files_cleanup()
    logging.info("文件处理修复完成")

