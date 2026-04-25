import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
USERS_FILE = DATA_DIR / "users.xlsx"
BILLS_DIR = DATA_DIR / "bills"

DEFAULT_PAYMENT_METHODS = [
    "微信", "支付宝", "银行卡", "现金", "信用卡", "花呗", "云闪付", "其他"
]

DEFAULT_CATEGORIES = [
    "餐饮", "交通", "购物", "日用品", "娱乐", "房租", "水电", 
    "学习", "医疗", "工资", "奖金", "兼职", "转账", "其他"
]

DEFAULT_TIME_SLOTS = [
    "00:00-06:00", "06:00-12:00", "12:00-18:00", "18:00-24:00"
]

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

SECRET_KEY = "jizhang-secret-key-2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BILLS_DIR.mkdir(parents=True, exist_ok=True)
