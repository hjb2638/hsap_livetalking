from sqlalchemy import create_engine, Column, Integer, Text, TIMESTAMP
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete


from datetime import datetime
from typing import List, Optional
# 数据库配置
DATABASE_URL = "mysql+pymysql://hsap:yanshandaxue@localhost:3306/hsap"

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600
)

# 创建会话工厂
SessionLocal = sessionmaker(autoflush=False, bind=engine)

# 基类模型
Base = declarative_base()


# 数据模型定义
class QaData(Base):
    __tablename__ = "qa_data"

    user_id = Column(Integer, primary_key=True, index=True,nullable=False)
    hra_qa_data = Column(Text, nullable=True)
    qa_date = Column(TIMESTAMP(6), nullable=True)
    hra_report_data = Column(Text, nullable=True)
    report_date = Column(TIMESTAMP(6), nullable=True)

class HraData(Base):
    __tablename__ = "hra_data"
    user_id = Column(Integer, primary_key=True, index=True,nullable=False)
    hra_data = Column(Text, nullable=True)
    hra_date = Column(TIMESTAMP(6), nullable=True)


# 创建 HRA 数据
def create_hra_data(db: Session, user_id: int, hra_data: str):
    db=next(get_db())
    db_hra = HraData(
        user_id=user_id,
        hra_data=hra_data,
        hra_date=datetime.now()
    )
    db.add(db_hra)
    db.commit()
    db.refresh(db_hra)
    return db_hra

# 获取单个用户的 HRA 数据
def get_hra_data_by_user_id(db: Session, user_id: int):
    db = next(get_db())
    return db.query(HraData).filter(HraData.user_id == user_id).first()

# 获取所有 HRA 数据
def get_all_hra_data(db: Session, skip: int = 0, limit: int = 100):
    return db.query(HraData).offset(skip).limit(limit).all()

# 更新 HRA 数据
def update_hra_data(db: Session, user_id: int, hra_data: str):
    db = next(get_db())
    db_hra = db.query(HraData).filter(HraData.user_id == user_id).first()
    if db_hra:
        db_hra.hra_data = hra_data
        db_hra.hra_date = datetime.now()
        db.commit()
        db.refresh(db_hra)
    return db_hra

# 删除 HRA 数据
def delete_hra_data(db: Session, user_id: int):
    db_hra = db.query(HraData).filter(HraData.user_id == user_id).first()
    if db_hra:
        db.delete(db_hra)
        db.commit()
    return db_hra

# def create_hra_data(
#         session: Session,
#         user_id: int,
#         hra_data: Optional[str] = None,
#         hra_date: Optional[datetime] = None
# ) -> HraData:
#     """创建新的 HRA 数据记录"""
#     if not hra_date:
#         hra_date = datetime.now()
#
#     hra_record = HraData(
#         user_id=user_id,
#         hra_data=hra_data,
#         hra_date=hra_date
#     )
#
#     session.add(hra_record)
#     session.commit()
#     session.refresh(hra_record)
#     return hra_record
#
#
# def get_hra_data_by_user_id(
#         session: Session,
#         user_id: int
# ) -> Optional[HraData]:
#     """根据用户 ID 获取 HRA 数据"""
#     query = select(HraData).where(HraData.user_id == user_id)
#     result = session.execute(query)
#     return result.scalar_one_or_none()
#
#
# def get_all_hra_data(
#         session: Session,
#         skip: int = 0,
#         limit: int = 100
# ) -> List[HraData]:
#     """获取所有 HRA 数据记录"""
#     query = select(HraData).offset(skip).limit(limit)
#     result = session.execute(query)
#     return result.scalars().all()
#
#
# def update_hra_data(
#         session: Session,
#         user_id: int,
#         hra_data: Optional[str] = None,
#         hra_date: Optional[datetime] = None
# ) -> Optional[HraData]:
#     """更新 HRA 数据记录"""
#     query = update(HraData).where(HraData.user_id == user_id)
#
#     update_values = {}
#     if hra_data is not None:
#         update_values["hra_data"] = hra_data
#     if hra_date is not None:
#         update_values["hra_date"] = hra_date
#
#     if update_values:
#         query = query.values(update_values)
#         query.execution_options(synchronize_session="fetch")
#         session.execute(query)
#         session.commit()
#
#     return get_hra_data_by_user_id(session, user_id)
#
#
# def delete_hra_data(
#         session: Session,
#         user_id: int
# ) -> bool:
#     """删除 HRA 数据记录"""
#     query = delete(HraData).where(HraData.user_id == user_id)
#     result = session.execute(query)
#     session.commit()
#     return result.rowcount > 0


# 获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 增删改查操作
def create_qa_data(
        db: Session,
        user_id: int,
        hra_qa_data: str = '',
        hra_report_data: str = '',
        qa_date: datetime = None,
        report_date: datetime = None,
):
    db_qa = QaData(
        user_id=user_id,
        hra_qa_data=hra_qa_data,
        hra_report_data=hra_report_data,
        qa_date=qa_date ,
        report_date=report_date,
    )
    db_qa1 = db.query(QaData).filter(QaData.user_id == user_id).first()
    print(db_qa1)
    if db_qa1 is not None:
        db_qa1.hra_qa_data = hra_qa_data
        db_qa1.qa_date = qa_date
        db_qa1.report_date = report_date
        db_qa1.hra_report_data = hra_report_data
        db.commit()
        db.refresh(db_qa1)
        return db_qa1
    else:
        db.add(db_qa)
        db.commit()
        db.refresh(db_qa)
        return db_qa


def get_qa_data(db: Session, user_id: int):
    return db.query(QaData).filter(QaData.user_id == user_id).first()


def get_qa_data_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(QaData).filter(QaData.user_id == user_id).offset(skip).limit(limit).all()


def update_qa_data(
        db: Session,
        user_id: int = None,
        hra_qa_data: str = None,
        hra_report_data: str = None,
        qa_date: datetime = None,
        report_date: datetime = None
):
    db_qa = db.query(QaData).filter(QaData.user_id == user_id).first()
    if not db_qa:
        return None

    if user_id is not None:
        db_qa.user_id = user_id
    if hra_qa_data is not None:
        db_qa.hra_qa_data = hra_qa_data
    if hra_report_data is not None:
        db_qa.hra_report_data = hra_report_data
    if qa_date is not None:
        db_qa.qa_date = qa_date
    if report_date is not None:
        db_qa.report_date = report_date

    db.commit()
    db.refresh(db_qa)
    return db_qa


def delete_qa_data(db: Session, user_id: int):
    db_qa = db.query(QaData).filter(QaData.user_id == user_id).first()
    if not db_qa:
        return False

    db.delete(db_qa)
    db.commit()
    return True


# 创建表（如果不存在）
def create_tables():
    Base.metadata.create_all(bind=engine)


# 示例使用
if __name__ == "__main__":
    create_tables()

    db = next(get_db())
    try:
        # 创建记录
        new_record = create_qa_data(
            db=db,
            user_id=1,
            hra_qa_data='{"question1": "answer1"}',
            hra_report_data='{"risk": "low"}'
        )
        print(f"创建的记录ID: {new_record.user_id}")

        # 查询记录
        record = get_qa_data(db, new_record.user_id)
        print(f"查询结果: {record.hra_qa_data}")
    finally:
        db.close()