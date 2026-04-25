import random
from datetime import datetime, timedelta
from pathlib import Path

from config import (
    USERS_FILE, BILLS_DIR,
    DEFAULT_PAYMENT_METHODS, DEFAULT_CATEGORIES, DEFAULT_TIME_SLOTS,
    ensure_dirs
)
from excel_storage import ExcelStorage, storage
from models import TransactionType


def generate_test_bill(bill_id: int) -> dict:
    is_income = random.random() < 0.2
    
    if is_income:
        transaction_type = TransactionType.income.value
        income_categories = ["工资", "奖金", "兼职", "转账", "其他"]
        category = random.choice(income_categories)
        amount = round(random.uniform(500, 15000), 2)
        remark_choices = ["", "月度工资", "项目奖金", "兼职收入", "朋友转账", "理财收益", "红包"]
    else:
        transaction_type = TransactionType.expense.value
        expense_categories = ["餐饮", "交通", "购物", "日用品", "娱乐", "房租", "水电", "学习", "医疗", "其他"]
        category = random.choice(expense_categories)
        
        if category == "餐饮":
            amount = round(random.uniform(15, 200), 2)
        elif category == "交通":
            amount = round(random.uniform(5, 80), 2)
        elif category == "购物":
            amount = round(random.uniform(50, 500), 2)
        elif category == "日用品":
            amount = round(random.uniform(20, 150), 2)
        elif category == "娱乐":
            amount = round(random.uniform(30, 300), 2)
        elif category == "房租":
            amount = round(random.uniform(1000, 4000), 2)
        elif category == "水电":
            amount = round(random.uniform(50, 300), 2)
        elif category == "学习":
            amount = round(random.uniform(50, 500), 2)
        elif category == "医疗":
            amount = round(random.uniform(30, 500), 2)
        else:
            amount = round(random.uniform(10, 200), 2)
        
        remark_choices = [
            "", "午餐", "晚餐", "早餐", "外卖",
            "地铁", "公交", "打车", "共享单车",
            "超市购物", "网购", "水果", "零食",
            "电影票", "KTV", "游戏充值",
            "学费", "书籍", "课程",
            "药品", "体检", "医院挂号",
            "电费", "水费", "网费",
            "其他支出", "忘记记什么了"
        ]
    
    remark = random.choice(remark_choices)
    if random.random() < 0.3:
        remark = ""
    
    payment_method = random.choice(DEFAULT_PAYMENT_METHODS)
    payment_time = random.choice(DEFAULT_TIME_SLOTS)
    
    return {
        "id": bill_id,
        "transaction_type": transaction_type,
        "amount": amount,
        "payment_time": payment_time,
        "payment_method": payment_method,
        "category": category,
        "remark": remark or None
    }


def generate_test_data():
    print("=" * 60)
    print("正在生成测试数据...")
    print("=" * 60)
    
    ensure_dirs()
    
    if USERS_FILE.exists():
        print(f"\n删除旧的用户文件: {USERS_FILE}")
        USERS_FILE.unlink()
    
    for bill_file in BILLS_DIR.glob("*_bills.xlsx"):
        print(f"删除旧的账单文件: {bill_file.name}")
        bill_file.unlink()
    
    options_file = Path(__file__).resolve().parent / "data" / "options.xlsx"
    if options_file.exists():
        options_file.unlink()
    
    global storage
    storage = ExcelStorage()
    
    test_users = [
        ("user1", "123456"),
        ("user2", "123456"),
        ("user3", "123456")
    ]
    
    for username, password in test_users:
        print(f"\n创建用户: {username}")
        user = storage.create_user(username, password)
        print(f"  用户ID: {user.id}")
        
        print(f"  生成 100 条测试账单...")
        for i in range(1, 101):
            bill_data = generate_test_bill(i)
            storage.create_bill(username, bill_data)
        
        bills = storage.get_bills(username)
        income_count = sum(1 for b in bills if b.transaction_type == TransactionType.income)
        expense_count = len(bills) - income_count
        income_total = sum(b.amount for b in bills if b.transaction_type == TransactionType.income)
        expense_total = sum(b.amount for b in bills if b.transaction_type == TransactionType.expense)
        
        print(f"  账单总数: {len(bills)}")
        print(f"  收入: {income_count} 条, 总计: {income_total:.2f} 元")
        print(f"  支出: {expense_count} 条, 总计: {expense_total:.2f} 元")
        print(f"  净余额: {income_total - expense_total:.2f} 元")
    
    print("\n" + "=" * 60)
    print("测试数据生成完成！")
    print("=" * 60)
    print("\n测试账号信息：")
    print(f"  管理员账号: admin / admin123")
    print(f"  普通用户1: user1 / 123456")
    print(f"  普通用户2: user2 / 123456")
    print(f"  普通用户3: user3 / 123456")
    
    print("\n数据文件位置：")
    print(f"  用户信息表: {USERS_FILE}")
    print(f"  账单目录: {BILLS_DIR}")


if __name__ == "__main__":
    generate_test_data()
