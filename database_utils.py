from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, Text, TIMESTAMP, select
from datetime import datetime
from typing import List, Optional

# 数据库配置 - 使用异步驱动
DATABASE_URL = "mysql+asyncmy://hsap:yanshandaxue@localhost:3306/hsap"

# 创建异步数据库引擎
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False  # 设置为True可以查看SQL语句
)

# 创建异步会话工厂
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# 基类模型
Base = declarative_base()


# 数据模型定义
class QaData(Base):
    __tablename__ = "qa_data"

    user_id = Column(Integer, primary_key=True, index=True, nullable=False)
    hra_qa_data = Column(Text, nullable=True)
    qa_date = Column(TIMESTAMP(6), nullable=True)
    hra_report_data = Column(Text, nullable=True)
    report_date = Column(TIMESTAMP(6), nullable=True)
    hra_report_summary = Column(Text, nullable=True)


class HraData(Base):
    __tablename__ = "hra_data"
    user_id = Column(Integer, primary_key=True, index=True, nullable=False)
    hra_data = Column(Text, nullable=True)
    hra_date = Column(TIMESTAMP(6), nullable=True)

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "hra_data": self.hra_data,
            "hra_date": self.hra_date,
        }


# 获取异步数据库会话
async def get_db():
    async with async_session() as session:
        yield session


# 创建 HRA 数据
async def create_hra_data(user_id: int, hra_data: str):
    async with async_session() as session:
        db_hra = HraData(
            user_id=user_id,
            hra_data=hra_data,
            hra_date=datetime.now()
        )
        session.add(db_hra)
        await session.commit()
        await session.refresh(db_hra)
        return db_hra


# 获取单个用户的 HRA 数据
async def get_hra_data_by_user_id(user_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(HraData).filter(HraData.user_id == user_id)
        )
        return result.scalar_one_or_none()


# 获取所有 HRA 数据
async def get_all_hra_data(skip: int = 0, limit: int = 100):
    async with async_session() as session:
        result = await session.execute(
            select(HraData).offset(skip).limit(limit)
        )
        return result.scalars().all()


# 更新 HRA 数据
async def update_hra_data(user_id: int, hra_data: str):
    async with async_session() as session:
        db_hra = await session.get(HraData, user_id)
        if db_hra:
            db_hra.hra_data = hra_data
            db_hra.hra_date = datetime.now()
            await session.commit()
            await session.refresh(db_hra)
        return db_hra


# 删除 HRA 数据
async def delete_hra_data(user_id: int):
    async with async_session() as session:
        db_hra = await session.get(HraData, user_id)
        if db_hra:
            await session.delete(db_hra)
            await session.commit()
            return True
        return False


# 增删改查操作
async def create_qa_data(
        user_id: int,
        hra_qa_data: str = '',
        hra_report_data: str = '',
        qa_date: datetime = None,
        report_date: datetime = None,
):
    async with async_session() as session:
        db_qa = await session.get(QaData, user_id)
        if db_qa:
            db_qa.hra_qa_data = hra_qa_data
            db_qa.hra_report_data = hra_report_data
            db_qa.qa_date = qa_date
            db_qa.report_date = report_date
        else:
            db_qa = QaData(
                user_id=user_id,
                hra_qa_data=hra_qa_data,
                hra_report_data=hra_report_data,
                qa_date=qa_date,
                report_date=report_date,
            )
            session.add(db_qa)
        await session.commit()
        await session.refresh(db_qa)
        return db_qa


async def get_qa_data(user_id: int):
    async with async_session() as session:
        return await session.get(QaData, user_id)


async def get_qa_data_by_user(user_id: int, skip: int = 0, limit: int = 100):
    async with async_session() as session:
        result = await session.execute(
            select(QaData).filter(QaData.user_id == user_id).offset(skip).limit(limit)
        )
        return result.scalars().all()


async def update_qa_data(
        user_id: int = None,
        hra_qa_data: str = None,
        hra_report_data: str = None,
        qa_date: datetime = None,
        report_date: datetime = None
):
    async with async_session() as session:
        db_qa = await session.get(QaData, user_id)
        if not db_qa:
            return None

        if hra_qa_data is not None:
            db_qa.hra_qa_data = hra_qa_data
        if hra_report_data is not None:
            db_qa.hra_report_data = hra_report_data
        if qa_date is not None:
            db_qa.qa_date = qa_date
        if report_date is not None:
            db_qa.report_date = report_date

        await session.commit()
        await session.refresh(db_qa)
        return db_qa


async def delete_qa_data(user_id: int):
    async with async_session() as session:
        db_qa = await session.get(QaData, user_id)
        if not db_qa:
            return False

        await session.delete(db_qa)
        await session.commit()
        return True


# 创建表（如果不存在）
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# 示例使用
async def main():
    await create_tables()

    try:
        # 创建记录
        new_record = await create_qa_data(
            user_id=1,
            hra_qa_data='{"question1": "answer1"}',
            hra_report_data='{"risk": "low"}'
        )
        print(f"创建的记录ID: {new_record.user_id}")

        # 查询记录
        record = await get_qa_data(new_record.user_id)
        print(f"查询结果: {record.hra_qa_data}")
    finally:
        pass


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
