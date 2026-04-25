from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from enum import Enum


class TransactionType(str, Enum):
    income = "收入"
    expense = "支出"


class Role(str, Enum):
    admin = "管理员"
    user = "普通用户"


class User(BaseModel):
    id: int
    username: str
    password: str
    role: Role
    created_at: datetime


class UserCreate(BaseModel):
    username: str
    password: str


class UserUpdate(BaseModel):
    password: Optional[str] = None


class Bill(BaseModel):
    id: int
    transaction_type: TransactionType
    amount: float
    payment_time: str
    payment_method: str
    category: str
    remark: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class BillCreate(BaseModel):
    transaction_type: TransactionType
    amount: float
    payment_time: str
    payment_method: str
    category: str
    remark: Optional[str] = None


class BillUpdate(BaseModel):
    transaction_type: Optional[TransactionType] = None
    amount: Optional[float] = None
    payment_time: Optional[str] = None
    payment_method: Optional[str] = None
    category: Optional[str] = None
    remark: Optional[str] = None


class CategoryOption(BaseModel):
    name: str


class BillListResponse(BaseModel):
    bills: List[Bill]
    total_amount: float
    count: int


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
