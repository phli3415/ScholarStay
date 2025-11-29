# """
# 数据库工具函数
# 包含常用的数据库操作辅助函数
# """
#
# from typing import Optional
# from model.user import User
# from model.houses import Houses
# from model.bookmark import Bookmark
# from model.chat_history import ChatHistory
#
#
# async def get_user_by_gmail(gmail: str) -> Optional[User]:
#     """
#     根据gmail获取用户
#
#     Args:
#         gmail: 用户的gmail地址
#
#     Returns:
#         User对象或None
#     """
#     return await User.filter(gmail=gmail).first()
#
#
# async def get_listing_by_id(listing_id: int) -> Optional[Houses]:
#     """
#     根据ID获取房源
#
#     Args:
#         listing_id: 房源ID
#
#     Returns:
#         Listing对象或None
#     """
#     return await Houses.filter(id=listing_id).first()
#
#
# async def get_user_bookmarks(user_id: int) -> list[Bookmark]:
#     """
#     获取用户的所有书签
#
#     Args:
#         user_id: 用户ID
#
#     Returns:
#         书签列表
#     """
#     return await Bookmark.filter(user_id=user_id).prefetch_related("listing").all()
#
#
# async def get_user_chat_sessions(user_id: int, limit: int = 10) -> list[ChatHistory]:
#     """
#     获取用户的聊天会话列表
#
#     Args:
#         user_id: 用户ID
#         limit: 返回数量限制
#
#     Returns:
#         聊天会话列表（按创建时间倒序）
#     """
#     return await ChatHistory.filter(user_id=user_id).order_by("-created_at").limit(limit).all()
#
#
# async def get_chat_session_by_id(session_id: str) -> Optional[ChatHistory]:
#     """
#     根据会话ID获取聊天会话
#
#     Args:
#         session_id: 会话ID
#
#     Returns:
#         ChatHistory对象或None
#     """
#     return await ChatHistory.filter(session_id=session_id).first()
#
#
# async def search_listings(
#     province: Optional[str] = None,
#     city: Optional[str] = None,
#     max_rent: Optional[float] = None,
#     min_rent: Optional[float] = None,
#     has_kitchen: Optional[bool] = None,
#     has_washer: Optional[bool] = None,
#     has_parking: Optional[bool] = None,
#     is_rented: Optional[bool] = None,
#     max_distance: Optional[float] = None,
#     limit: int = 20,
#     offset: int = 0,
# ) -> list[Houses]:
#     """
#     搜索房源
#
#     Args:
#         province: 省份筛选
#         city: 城市筛选
#         max_rent: 最大租金
#         min_rent: 最小租金
#         has_kitchen: 是否有厨房
#         has_washer: 是否有洗衣机
#         has_parking: 是否有车位
#         is_rented: 是否已出租
#         max_distance: 最大距离（公里）
#         limit: 返回数量限制
#         offset: 偏移量
#
#     Returns:
#         房源列表
#     """
#     query = Houses.all()
#
#     if province:
#         query = query.filter(province=province)
#     if city:
#         query = query.filter(city=city)
#     if max_rent:
#         query = query.filter(monthly_rent__lte=max_rent)
#     if min_rent:
#         query = query.filter(monthly_rent__gte=min_rent)
#     if has_kitchen is not None:
#         query = query.filter(has_kitchen=has_kitchen)
#     if has_washer is not None:
#         query = query.filter(has_washer=has_washer)
#     if has_parking is not None:
#         query = query.filter(has_parking=has_parking)
#     if is_rented is not None:
#         query = query.filter(is_rented=is_rented)
#     if max_distance:
#         query = query.filter(distance_to_university__lte=max_distance)
#
#     return await query.limit(limit).offset(offset).all()
#
