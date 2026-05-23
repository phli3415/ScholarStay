from typing import List
import numpy as np
from langchain_chroma import Chroma
from langchain.tools.retriever import create_retriever_tool
from langchain_core.tools import tool
from .config import Config


def get_tools(llm_embedding):
    """
    创建并返回工具列表

    Args:
        llm_embedding: 嵌入模型实例，用于初始化向量存储

    Returns:
        list: 工具列表
        """

    # 创建 Chroma 向量存储实例
    vectorstore = Chroma(
        persist_directory=Config.CHROMADB_DIRECTORY,
        collection_name=Config.CHROMADB_COLLECTION_NAME,
        embedding_function=llm_embedding,
    )
    # 将向量存储转换为检索器
    retriever = vectorstore.as_retriever()
    # 创建检索工具
    retriever_tool = create_retriever_tool(
        retriever,
        name="retrieve",
        description="这是健康档案查询工具，搜索并返回有关用户的健康档案信息。"
    )

    # 自定义 multiply 工具
    @tool
    def multiply(a: float, b: float) -> float:
        """这是计算两个数的乘积的工具，返回最终的计算结果"""
        return a * b

    # 新增的文本相似度匹配工具
    @tool
    def find_most_similar(user_input: str, house_ids: List[int]) -> str:
        """
        在给定的候选字符串列表中，找出与目标字符串在语义上最相似的一个。

        Args:
            target: 目标文本段落
            candidates: 待比较的字符串数组/列表

        Returns:
            str: 候选列表中最相似的字符串
        """
        if not house_ids:
            return "候选列表为空"

        # 1. 将目标文本和候选文本全部转换为 Embedding 向量
        target_embedding = np.array(llm_embedding.embed_query(target))
        candidates_embeddings = np.array(llm_embedding.embed_documents(candidates))

        # 2. 计算余弦相似度
        # 计算每个候选向量的模长
        target_norm = np.linalg.norm(target_embedding)
        candidates_norms = np.linalg.norm(candidates_embeddings, axis=1)

        # 避免除以 0 的情况
        if target_norm == 0 or np.any(candidates_norms == 0):
            return candidates[0]

        # 点积除以模长的乘积，得到余弦相似度列表
        dot_products = np.dot(candidates_embeddings, target_embedding)
        similarities = dot_products / (candidates_norms * target_norm)

        # 3. 找出相似度最大的索引
        most_similar_index = np.argmax(similarities)

        return candidates[most_similar_index]

    # 返回工具列表（包含新工具）
    return [retriever_tool, multiply, find_most_similar]