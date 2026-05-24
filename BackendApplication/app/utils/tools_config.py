from typing import List
import numpy as np
# from langchain_chroma import Chroma
from langchain.tools.retriever import create_retriever_tool
from langchain_core.tools import tool
from ..core.rag_pipeline import find_similar_listings
from ..repository.house_repository import HouseRepository
import copy

from .config import Config
from .Schema import HouseFilters

def get_tools(llm_embedding):
    """
    创建并返回工具列表

    Args:
        llm_embedding: 嵌入模型实例，用于初始化向量存储

    Returns:
        list: 工具列表
        """

    # # 创建 Chroma 向量存储实例
    # vectorstore = Chroma(
    #     persist_directory=Config.CHROMADB_DIRECTORY,
    #     collection_name=Config.CHROMADB_COLLECTION_NAME,
    #     embedding_function=llm_embedding,
    # )
    # # 将向量存储转换为检索器
    # retriever = vectorstore.as_retriever()
    # # 创建检索工具
    # retriever_tool = create_retriever_tool(
    #     retriever,
    #     name="retrieve",
    #     description="这是健康档案查询工具，搜索并返回有关用户的健康档案信息。"
    # )
    house_repository = HouseRepository()


    @tool
    async def find_most_similar_house(user_input: str, house_ids: List[int]) -> List[int]:
        """
        Among the provided houses, return the id of top three houses that matches user_input the best.

        Args:
            user_input: User's requirement
            house_ids: The ids of candidate houses

        Returns:
            List[int]: The ids of the top three houses that matches user_input
        """
        return await find_similar_listings(user_input, house_ids, top_k=Config.EMBEDDING_HOUSES_RETURN)

    @tool
    async def filter_houses (house_requirement: HouseFilters) -> List[int]:
        """
        return a list of ids of houses that matches the requirement.

        Args:
            house_requirement: The requirement of houses

        Returns:
            List[int]: The ids of houses that matches the requirement
        """
        return await house_repository.filter_houses_ids(
            province=house_requirement.province,
            city=house_requirement.city,
            street=house_requirement.street,
            max_monthly_rent = house_requirement.max_monthly_rent,
            has_kitchen = house_requirement.has_kitchen,
            has_washer = house_requirement.has_washer,
            has_parking = house_requirement.has_parking,
            max_distance_to_university = house_requirement.max_distance_to_university,
            is_rented= True
        )

    @tool
    async def loosen_requirement(house_requirement: HouseFilters, counters: int) -> HouseFilters:
        """
            return a loosen house requirement if there are no house sources in database meet the current requirement.

            Args:
                house_requirement: The original requirement of houses
                counters: The current counter, representing the number of time loosen_requirement has been triggered.

            Returns:
                HouseFilters: The new requirement with loosen requirements applied.
        """
        new_requirement = copy.deepcopy(house_requirement)
        if counters == 0:
            if house_requirement.max_monthly_rent:
                new_requirement.max_monthly_rent = int(house_requirement.max_monthly_rent * 1.15)

        elif counters == 1:
            if house_requirement.max_distance_to_university:
                new_requirement.max_distance_to_university = int(house_requirement.max_distance_to_university + 2)

        else:
            new_requirement.has_kitchen = new_requirement.has_washer = new_requirement.has_parking = None

        return new_requirement


    # 返回工具列表（包含新工具）
    return [find_most_similar_house, filter_houses, loosen_requirement]