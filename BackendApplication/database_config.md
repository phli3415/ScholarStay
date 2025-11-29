# 数据库配置说明

## 数据库设计概览

本项目使用PostgreSQL + pgvector作为数据库系统，使用Tortoise ORM进行数据库操作。

## 数据表结构

### 1. users (用户表)
- `id`: 主键
- `gmail`: 用户的gmail地址（唯一）
- `username`: 用户名
- `password_hash`: 加密后的密码
- `created_at`: 创建时间
- `updated_at`: 更新时间

### 2. listings (房源表)
- `id`: 主键
- `province`: 省份
- `city`: 城市
- `street`: 街道
- `house_number`: 门牌号
- `monthly_rent`: 月租金
- `has_kitchen`: 是否包含厨房（布尔值）
- `has_washer`: 是否包含洗衣机（布尔值）
- `has_parking`: 是否有车位（布尔值）
- `is_rented`: 是否已出租（布尔值）
- `distance_to_university`: 离大学的距离（公里）
- `description`: 房源描述文本
- `embedding_vector`: 房源描述的向量表示（用于RAG）
- `owner_id`: 房源创建者的用户ID（外键）
- `created_at`: 创建时间
- `updated_at`: 更新时间

**索引**:
- 复合索引: (province, city) - 用于按地区查询
- 索引: monthly_rent - 用于按租金查询
- 索引: is_rented - 用于按出租状态查询

### 3. bookmarks (书签表)
- `id`: 主键
- `user_id`: 用户ID（外键）
- `listing_id`: 房源ID（外键）
- `created_at`: 收藏时间

**唯一约束**: (user_id, listing_id) - 确保同一用户不能重复收藏同一房源

### 4. chat_histories (Agent聊天历史表)
- `id`: 主键
- `user_id`: 用户ID（外键）
- `session_id`: 会话唯一标识符（唯一）
- `title`: 会话标题
- `messages`: 聊天消息列表（JSON格式）
- `metadata`: 会话元数据（JSON格式，如筛选条件、比较的房源ID等）
- `created_at`: 会话创建时间
- `updated_at`: 最后更新时间

**索引**:
- 索引: user_id - 用于按用户查询
- 索引: created_at - 用于按创建时间查询

## pgvector扩展配置

### 安装pgvector扩展

在PostgreSQL数据库中执行：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 向量字段说明

当前设计使用`embedding_vector`字段存储向量，实际使用中建议：

1. **方案一：使用专门的向量列（推荐）**
   ```sql
   -- 在migration中添加向量列
   ALTER TABLE listings ADD COLUMN embedding vector(1536);
   -- 创建向量索引以加速相似度搜索
   CREATE INDEX ON listings USING ivfflat (embedding vector_cosine_ops);
   ```

2. **方案二：使用JSON字段存储向量**
   - 当前使用`embedding_vector`字段存储JSON格式的向量
   - 在应用层进行向量相似度计算

### RAG向量生成

房源描述的向量可以通过以下方式生成：
- 使用sentence-transformers或其他embedding模型
- 向量维度建议：384、512、768、1536（取决于使用的模型）
- 将房源的所有关键信息（地址、价格、设施、距离等）组合成描述文本

## 数据库连接配置

### 环境变量

在`.env`文件中配置数据库连接信息：

```env
DATABASE_URL=postgresql://user:password@localhost:5432/scholarstay
# 或
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=scholarstay
```

### Tortoise ORM配置

配置文件位置：`app/database.py`

## 数据库迁移

使用Aerich进行数据库迁移管理：

```bash
# 初始化Aerich
aerich init -t app.database.TORTOISE_ORM

# 初始化数据库
aerich init-db

# 创建迁移
aerich migrate

# 应用迁移
aerich upgrade
```

## 关系图

```
User (用户)
  ├── 1:N → Listing (房源)
  ├── 1:N → Bookmark (书签)
  └── 1:N → ChatHistory (聊天历史)

Listing (房源)
  ├── N:1 → User (创建者)
  └── 1:N → Bookmark (被收藏)

Bookmark (书签)
  ├── N:1 → User (用户)
  └── N:1 → Listing (房源)
```

## 注意事项

1. 确保PostgreSQL版本 >= 11（支持JSON字段）
2. 安装并启用pgvector扩展
3. 密码应该使用哈希存储，不要在数据库中存储明文密码
4. 定期备份数据库
5. 在生产环境中使用连接池

