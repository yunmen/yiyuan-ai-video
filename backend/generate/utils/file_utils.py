from pathlib import Path
from typing import Optional
from loguru import logger


def create_code_file(
    file_path: str | Path,
    content: str,
    encoding: str = "utf-8",
    overwrite: bool = False
) -> bool:
    """
    创建 FastAPI 相关文件（自动补全父目录）
    
    Args:
        file_path: 文件路径（如: "app/api/v1/users.py" 或 Path 对象）
        content: 要写入的文件内容（如: FastAPI 路由代码）
        encoding: 文件编码（默认 utf-8, 推荐用于中文/特殊字符）
        overwrite: 是否覆盖已存在的文件（默认 False，避免误删）
    
    Returns:
        bool: 操作成功返回 True, 失败返回 False
    
    Example:
        >>> create_crud_file(
                "app/api/v1/users.py",
                content="from fastapi import APIRouter\nrouter = APIRouter()",
                overwrite=True
            )
    """
    path = Path(file_path)
    
    try:
        # 自动补全父目录（递归创建不存在的目录）
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # 检查文件是否存在且不允许覆盖时，跳过写入
        if path.exists() and not overwrite:
            logger.warning(f"文件已存在且禁止覆盖: {path}")
            return False
        
        # 写入内容（覆盖模式）
        path.write_text(content, encoding=encoding)
        logger.info(f"文件创建/覆盖成功: {path}")
        return True
    
    except PermissionError:
        logger.warning(f"无权限操作文件: {path}（请检查文件/目录权限）")
        return False
    except Exception as e:
        logger.warning(f"文件创建失败: {path}，错误详情: {str(e)}")
        return False


def delete_code_file(file_path: str | Path) -> bool:
    """
    删除 FastAPI 相关文件（保留父目录）
    
    Args:
        file_path: 文件路径（如: "app/api/v1/users.py" 或 Path 对象）
    
    Returns:
        bool: 操作成功返回 True, 失败返回 False
    
    Example:
        >>> delete_fastapi_file("app/api/v1/users.py")
    """
    path = Path(file_path)
    
    try:
        # 检查路径是否存在且是文件（避免误删目录）
        if not path.exists():
            logger.warning(f"文件不存在，无需删除: {path}")
            return False
        if not path.is_file():
            logger.warning(f"路径不是文件，禁止删除: {path}（可能是目录）")
            return False
        
        # 执行删除
        path.unlink()
        logger.info(f"文件删除成功: {path}")
        return True
    
    except PermissionError:
        logger.warning(f"无权限删除文件: {path}（请检查文件/目录权限）")
        return False
    except Exception as e:
        logger.warning(f"文件删除失败: {path}，错误详情: {str(e)}")
        return False
