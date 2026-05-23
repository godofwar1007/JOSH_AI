from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any
import enum
from fastapi import FastAPI,Depends,HTTPException
from pydantic import BaseModel,EmailStr,Field
from sqlalchemy import String,Integer,JSON,select,update,delete,func
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker,AsyncSession
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column

# database setup 
db_url="postgresql+asyncpg://postgres:mysecretpassword@localhost/orcr_data"
engine=create_async_engine(db_url,echo=True)
LocalSession=async_sessionmaker(engine,expire_on_commit=True)

# so some schemas 

class Base(DeclarativeBase):
    pass

class Gender(str,enum.Enum):
    male="Male"
    female="Female"

class Category(str,enum.Enum):
    OPEN = "OPEN"
    EWS = "GEN-EWS"
    OBC_NCL = "OBC-NCL"
    SC = "SC"
    ST = "ST"
    OPEN_PwD = "OPEN(PwD)"
    EWS_PwD = "GEN-EWS(PwD)"
    OBC_NCL_PwD = "OBC-NCL(PwD)"
    SC_PwD = "SC(PwD)"
    ST_PwD = "ST(PwD)"

class User(Base):
    __tablename__="users"

    id:Mapped[int]=mapped_column(primary_key=True,index=True)
    name:Mapped[str]=mapped_column(String(100),nullable=False)
    email:Mapped[str]=mapped_column(String(100),unique=True,index=True,nullable=False)
    adv_rank:Mapped[int]=mapped_column(Integer,nullable=False)
    mains_rank:Mapped[int]=mapped_column(Integer,nullable=True)
    category:Mapped[Category]=mapped_column(nullable=False)
    gender:Mapped[Gender]=mapped_column(nullable=False)
    preferred_branches:Mapped[List[str]]=mapped_column(JSON,default=list)
    
    queries_today: Mapped[int] = mapped_column(Integer, default=0)
    cooldown_until: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_query: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())

class usage_schema(BaseModel):
    queries_today:int=0
    cooldown_until:Optional[datetime]=None
    last_query:Optional[datetime]=None

class create_schema(BaseModel):
    name:str
    email:EmailStr
    adv_rank:int
    mains_rank:Optional[int]=None
    category:Category
    gender:Gender
    preferred_branches:List[str]=[]
    usage:usage_schema=Field(default_factory=usage_schema)

class upadate_schema(BaseModel):
    name:Optional[str]=None
    adv_rank:Optional[int]=None
    mains_rank:Optional[int]=None
    category:Optional[Category]=None
    gender:Optional[Gender]=None
    preferred_branches:Optional[List[str]]=None
    usage:Optional[usage_schema]=None

class response_schema(BaseModel):
    id:int
    name:str
    email:str
    adv_rank:int
    mains_rank:Optional[int]
    category:Category
    gender:Gender
    preferred_branches:List[str]
    updated_at:Optional[datetime]
    usage:usage_schema

    class Config:
        form_attributes=True # so apparantly this is essential so that orm to convert the db response to format that 
                             # that our endpoint expects ....which is Pydantic i guess

async def create_user(db:AsyncSession,user_data:create_schema) -> User:

    usage=user_data.usage
    db_user=User(
        name=user_data.name,
        email=user_data.email,
        adv_rank=user_data.adv_rank,
        mains_rank=user_data.mains_rank,
        category=user_data.gender,
        preferred_branches=user_data.preferred_branches,
        queries_today=usage.queries_today,
        cooldown_until=usage.cooldown_until,
        last_query=usage.last_query,

    )

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    print("user created :D")
    return db_user

async def get_by_email(db:AsyncSession,email:str)->Optional[User]:

    idk=select(User).where(User.email==email)
    result=await db.execute(idk)
    return result.scalar_one_or_none()

async def get_by_id(db:AsyncSession,user_id:int)->Optional[User]:

    idk=select(User).where(User.id==user_id)
    result=await db.execute(idk)
    return result.scalar_one_or_none()
   

async def update_user(db:AsyncSession,user_id:int,update_data:upadate_schema) -> Optional[User]:

    user = await get_by_id(db,user_id) # fetching the user from db
    if not user:
        return None
    
    # updating where we are supposed to update ofc!
    if update_data.name is not None:
        user.name = update_data.name
    if update_data.adv_rank is not None:
        user.adv_rank = update_data.adv_rank
    if update_data.mains_rank is not None:
        user.mains_rank = update_data.mains_rank
    if update_data.category is not None:
        user.category = update_data.category
    if update_data.gender is not None:
        user.gender = update_data.gender
    if update_data.preferred_branches is not None:
        user.preferred_branches = update_data.preferred_branches
    if update_data.usage is not None:
        user.queries_today = update_data.usage.queries_today
        user.cooldown_until = update_data.usage.cooldown_until
        user.last_query = update_data.usage.last_query

    user.updated_at=func.now()
    await db.commit()
    await db.refresh(user)
    print("user updated :D")
    return user    

async def delete_user(db: AsyncSession, user_id: int)->bool:

    idk=delete(User).where(User.id==user_id).returning(User.id)
    result=await db.execute(idk)
    deleted_ids=result.fetchall()
    await db.commit()
    if deleted_ids:
        print("user deleted :D")
        return True
    else:
        print("user not found :(")
        return False 
        
async def get_db()-> AsyncSession:  # func to provide the session to fastapi request
    async with LocalSession() as session:
        return session
    
    







