import os
import pandas as pd
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from config import (
    USERS_FILE, BILLS_DIR, 
    DEFAULT_PAYMENT_METHODS, DEFAULT_CATEGORIES, DEFAULT_TIME_SLOTS,
    ADMIN_USERNAME, ADMIN_PASSWORD, ensure_dirs
)
from models import User, Bill, Role, TransactionType


class ExcelStorage:
    def __init__(self):
        ensure_dirs()
        self._init_users_file()
        self._init_options_file()

    def _init_users_file(self):
        if not USERS_FILE.exists():
            df = pd.DataFrame({
                'id': [1],
                'username': [ADMIN_USERNAME],
                'password': [ADMIN_PASSWORD],
                'role': [Role.admin.value],
                'created_at': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
            })
            df.to_excel(USERS_FILE, index=False)

    def _init_options_file(self):
        options_file = Path(__file__).resolve().parent / "data" / "options.xlsx"
        if not options_file.exists():
            with pd.ExcelWriter(options_file) as writer:
                pd.DataFrame({'method': DEFAULT_PAYMENT_METHODS}).to_excel(
                    writer, sheet_name='payment_methods', index=False
                )
                pd.DataFrame({'category': DEFAULT_CATEGORIES}).to_excel(
                    writer, sheet_name='categories', index=False
                )
                pd.DataFrame({'time_slot': DEFAULT_TIME_SLOTS}).to_excel(
                    writer, sheet_name='time_slots', index=False
                )

    def get_users(self) -> List[User]:
        if not USERS_FILE.exists():
            return []
        df = pd.read_excel(USERS_FILE)
        users = []
        for _, row in df.iterrows():
            users.append(User(
                id=int(row['id']),
                username=str(row['username']),
                password=str(row['password']),
                role=Role(row['role']),
                created_at=pd.to_datetime(row['created_at'])
            ))
        return users

    def get_user_by_username(self, username: str) -> Optional[User]:
        users = self.get_users()
        for user in users:
            if user.username == username:
                return user
        return None

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        users = self.get_users()
        for user in users:
            if user.id == user_id:
                return user
        return None

    def create_user(self, username: str, password: str) -> User:
        users = self.get_users()
        new_id = max([u.id for u in users], default=0) + 1
        
        new_user = User(
            id=new_id,
            username=username,
            password=password,
            role=Role.user,
            created_at=datetime.now()
        )
        
        users.append(new_user)
        
        df = pd.DataFrame([{
            'id': u.id,
            'username': u.username,
            'password': u.password,
            'role': u.role.value,
            'created_at': u.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for u in users])
        df.to_excel(USERS_FILE, index=False)
        
        self._create_user_bill_file(username)
        
        return new_user

    def _create_user_bill_file(self, username: str):
        bill_file = BILLS_DIR / f"{username}_bills.xlsx"
        if not bill_file.exists():
            df = pd.DataFrame({
                'id': pd.Series(dtype='int64'),
                'transaction_type': pd.Series(dtype='str'),
                'amount': pd.Series(dtype='float64'),
                'payment_time': pd.Series(dtype='str'),
                'payment_method': pd.Series(dtype='str'),
                'category': pd.Series(dtype='str'),
                'remark': pd.Series(dtype='str'),
                'created_at': pd.Series(dtype='str'),
                'updated_at': pd.Series(dtype='str')
            })
            df.to_excel(bill_file, index=False)

    def delete_user(self, user_id: int) -> bool:
        users = self.get_users()
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        if user.role == Role.admin:
            return False
        
        users = [u for u in users if u.id != user_id]
        
        if len(users) == 0:
            if USERS_FILE.exists():
                USERS_FILE.unlink()
        else:
            df = pd.DataFrame([{
                'id': u.id,
                'username': u.username,
                'password': u.password,
                'role': u.role.value,
                'created_at': u.created_at.strftime('%Y-%m-%d %H:%M:%S')
            } for u in users])
            df.to_excel(USERS_FILE, index=False)
        
        bill_file = BILLS_DIR / f"{user.username}_bills.xlsx"
        if bill_file.exists():
            bill_file.unlink()
        
        return True

    def update_user_password(self, user_id: int, new_password: str) -> bool:
        users = self.get_users()
        for user in users:
            if user.id == user_id:
                user.password = new_password
                df = pd.DataFrame([{
                    'id': u.id,
                    'username': u.username,
                    'password': u.password,
                    'role': u.role.value,
                    'created_at': u.created_at.strftime('%Y-%m-%d %H:%M:%S')
                } for u in users])
                df.to_excel(USERS_FILE, index=False)
                return True
        return False

    def _get_bill_file(self, username: str) -> Path:
        return BILLS_DIR / f"{username}_bills.xlsx"

    def get_bills(self, username: str, category: Optional[str] = None) -> List[Bill]:
        bill_file = self._get_bill_file(username)
        if not bill_file.exists():
            return []
        
        df = pd.read_excel(bill_file)
        if df.empty:
            return []
        
        if category and category != "全部":
            df = df[df['category'] == category]
        
        bills = []
        for _, row in df.iterrows():
            remark = row.get('remark', '')
            if pd.isna(remark):
                remark = ''
            
            bills.append(Bill(
                id=int(row['id']),
                transaction_type=TransactionType(row['transaction_type']),
                amount=float(row['amount']),
                payment_time=str(row['payment_time']),
                payment_method=str(row['payment_method']),
                category=str(row['category']),
                remark=str(remark) if remark else None,
                created_at=pd.to_datetime(row['created_at']),
                updated_at=pd.to_datetime(row['updated_at'])
            ))
        
        bills.sort(key=lambda x: x.created_at, reverse=True)
        return bills

    def get_bill_by_id(self, username: str, bill_id: int) -> Optional[Bill]:
        bills = self.get_bills(username)
        for bill in bills:
            if bill.id == bill_id:
                return bill
        return None

    def create_bill(self, username: str, bill_data: dict) -> Bill:
        bills = self.get_bills(username)
        new_id = max([b.id for b in bills], default=0) + 1
        now = datetime.now()
        
        new_bill = Bill(
            id=new_id,
            transaction_type=TransactionType(bill_data['transaction_type']),
            amount=float(bill_data['amount']),
            payment_time=bill_data['payment_time'],
            payment_method=bill_data['payment_method'],
            category=bill_data['category'],
            remark=bill_data.get('remark'),
            created_at=now,
            updated_at=now
        )
        
        bills.append(new_bill)
        self._save_bills(username, bills)
        
        return new_bill

    def update_bill(self, username: str, bill_id: int, bill_data: dict) -> Optional[Bill]:
        bills = self.get_bills(username)
        for i, bill in enumerate(bills):
            if bill.id == bill_id:
                if 'transaction_type' in bill_data:
                    bill.transaction_type = TransactionType(bill_data['transaction_type'])
                if 'amount' in bill_data:
                    bill.amount = float(bill_data['amount'])
                if 'payment_time' in bill_data:
                    bill.payment_time = bill_data['payment_time']
                if 'payment_method' in bill_data:
                    bill.payment_method = bill_data['payment_method']
                if 'category' in bill_data:
                    bill.category = bill_data['category']
                if 'remark' in bill_data:
                    bill.remark = bill_data['remark']
                
                bill.updated_at = datetime.now()
                bills[i] = bill
                
                self._save_bills(username, bills)
                return bill
        return None

    def delete_bill(self, username: str, bill_id: int) -> bool:
        bills = self.get_bills(username)
        original_count = len(bills)
        bills = [b for b in bills if b.id != bill_id]
        
        if len(bills) == original_count:
            return False
        
        self._save_bills(username, bills)
        return True

    def _save_bills(self, username: str, bills: List[Bill]):
        bill_file = self._get_bill_file(username)
        
        if not bills:
            df = pd.DataFrame({
                'id': pd.Series(dtype='int64'),
                'transaction_type': pd.Series(dtype='str'),
                'amount': pd.Series(dtype='float64'),
                'payment_time': pd.Series(dtype='str'),
                'payment_method': pd.Series(dtype='str'),
                'category': pd.Series(dtype='str'),
                'remark': pd.Series(dtype='str'),
                'created_at': pd.Series(dtype='str'),
                'updated_at': pd.Series(dtype='str')
            })
        else:
            df = pd.DataFrame([{
                'id': b.id,
                'transaction_type': b.transaction_type.value,
                'amount': b.amount,
                'payment_time': b.payment_time,
                'payment_method': b.payment_method,
                'category': b.category,
                'remark': b.remark or '',
                'created_at': b.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': b.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            } for b in bills])
        
        df.to_excel(bill_file, index=False)

    def get_payment_methods(self) -> List[str]:
        options_file = Path(__file__).resolve().parent / "data" / "options.xlsx"
        if not options_file.exists():
            return DEFAULT_PAYMENT_METHODS
        df = pd.read_excel(options_file, sheet_name='payment_methods')
        return df['method'].tolist()

    def add_payment_method(self, method: str) -> bool:
        methods = self.get_payment_methods()
        if method in methods:
            return False
        methods.append(method)
        
        options_file = Path(__file__).resolve().parent / "data" / "options.xlsx"
        df_methods = pd.DataFrame({'method': methods})
        
        df_categories = pd.read_excel(options_file, sheet_name='categories')
        df_time_slots = pd.read_excel(options_file, sheet_name='time_slots')
        
        with pd.ExcelWriter(options_file) as writer:
            df_methods.to_excel(writer, sheet_name='payment_methods', index=False)
            df_categories.to_excel(writer, sheet_name='categories', index=False)
            df_time_slots.to_excel(writer, sheet_name='time_slots', index=False)
        
        return True

    def get_categories(self) -> List[str]:
        options_file = Path(__file__).resolve().parent / "data" / "options.xlsx"
        if not options_file.exists():
            return DEFAULT_CATEGORIES
        df = pd.read_excel(options_file, sheet_name='categories')
        return df['category'].tolist()

    def add_category(self, category: str) -> bool:
        categories = self.get_categories()
        if category in categories:
            return False
        categories.append(category)
        
        options_file = Path(__file__).resolve().parent / "data" / "options.xlsx"
        df_categories = pd.DataFrame({'category': categories})
        
        df_methods = pd.read_excel(options_file, sheet_name='payment_methods')
        df_time_slots = pd.read_excel(options_file, sheet_name='time_slots')
        
        with pd.ExcelWriter(options_file) as writer:
            df_methods.to_excel(writer, sheet_name='payment_methods', index=False)
            df_categories.to_excel(writer, sheet_name='categories', index=False)
            df_time_slots.to_excel(writer, sheet_name='time_slots', index=False)
        
        return True

    def get_time_slots(self) -> List[str]:
        options_file = Path(__file__).resolve().parent / "data" / "options.xlsx"
        if not options_file.exists():
            return DEFAULT_TIME_SLOTS
        df = pd.read_excel(options_file, sheet_name='time_slots')
        return df['time_slot'].tolist()

    def add_time_slot(self, time_slot: str) -> bool:
        time_slots = self.get_time_slots()
        if time_slot in time_slots:
            return False
        time_slots.append(time_slot)
        
        options_file = Path(__file__).resolve().parent / "data" / "options.xlsx"
        df_time_slots = pd.DataFrame({'time_slot': time_slots})
        
        df_methods = pd.read_excel(options_file, sheet_name='payment_methods')
        df_categories = pd.read_excel(options_file, sheet_name='categories')
        
        with pd.ExcelWriter(options_file) as writer:
            df_methods.to_excel(writer, sheet_name='payment_methods', index=False)
            df_categories.to_excel(writer, sheet_name='categories', index=False)
            df_time_slots.to_excel(writer, sheet_name='time_slots', index=False)
        
        return True

    def get_user_categories(self, username: str) -> List[str]:
        bills = self.get_bills(username)
        categories = set()
        for bill in bills:
            categories.add(bill.category)
        return sorted(list(categories))


storage = ExcelStorage()
