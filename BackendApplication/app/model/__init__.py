"""
数据库模型模块
包含所有数据表的Tortoise ORM模型定义
"""

from user import User
from houses import Houses
from bookmark import Bookmark
from chat_history import ChatHistory

# 导出所有模型，供Aerich迁移工具使用
__all__ = [
    "User",
    "Houses",
    "Bookmark", 
    "ChatHistory",
]

# 定义模型的app名称，用于Tortoise ORM初始化
TORTOISE_ORM_MODELS = [
    "app.model.user",
    "app.model.houses",
    "app.model.bookmark",
    "app.model.chat_history",
]

