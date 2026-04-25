from fastapi import FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path

from config import SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES
from models import (
    User, Bill, Role, TransactionType,
    BillCreate, BillUpdate, UserCreate, BillListResponse
)
from excel_storage import storage


app = FastAPI(title="记账管理系统")

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


def get_current_user(request: Request) -> Optional[User]:
    username = request.session.get("username")
    if not username:
        return None
    return storage.get_user_by_username(username)


def require_user(request: Request) -> User:
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录，请先登录"
        )
    return user


def require_admin(request: Request) -> User:
    user = require_user(request)
    if user.role != Role.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return user


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    user = get_current_user(request)
    if user:
        if user.role == Role.admin:
            return RedirectResponse(url="/admin", status_code=302)
        return RedirectResponse(url="/bills", status_code=302)
    return RedirectResponse(url="/login", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = get_current_user(request)
    if user:
        if user.role == Role.admin:
            return RedirectResponse(url="/admin", status_code=302)
        return RedirectResponse(url="/bills", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    user = storage.get_user_by_username(username)
    if not user or user.password != password:
        return templates.TemplateResponse(
            "login.html", 
            {"request": request, "error": "用户名或密码错误"}
        )
    
    request.session["username"] = user.username
    
    if user.role == Role.admin:
        return RedirectResponse(url="/admin", status_code=302)
    return RedirectResponse(url="/bills", status_code=302)


@app.get("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


@app.get("/bills", response_class=HTMLResponse)
async def bills_page(request: Request, category: str = "全部"):
    user = require_user(request)
    if user.role == Role.admin:
        return RedirectResponse(url="/admin", status_code=302)
    
    bills = storage.get_bills(user.username, category if category != "全部" else None)
    
    income_total = sum(b.amount for b in bills if b.transaction_type == TransactionType.income)
    expense_total = sum(b.amount for b in bills if b.transaction_type == TransactionType.expense)
    net_total = income_total - expense_total
    
    user_categories = ["全部"] + storage.get_user_categories(user.username)
    all_categories = storage.get_categories()
    payment_methods = storage.get_payment_methods()
    time_slots = storage.get_time_slots()
    
    return templates.TemplateResponse("bills.html", {
        "request": request,
        "user": user,
        "bills": bills,
        "current_category": category,
        "categories": user_categories,
        "all_categories": all_categories,
        "payment_methods": payment_methods,
        "time_slots": time_slots,
        "income_total": round(income_total, 2),
        "expense_total": round(expense_total, 2),
        "net_total": round(net_total, 2),
        "transaction_types": [t.value for t in TransactionType]
    })


@app.post("/bills/create")
async def create_bill(
    request: Request,
    transaction_type: str = Form(...),
    amount: float = Form(...),
    payment_time: str = Form(...),
    payment_method: str = Form(...),
    category: str = Form(...),
    remark: str = Form(default="")
):
    user = require_user(request)
    if user.role == Role.admin:
        raise HTTPException(status_code=403, detail="管理员无法记账")
    
    bill_data = {
        "transaction_type": transaction_type,
        "amount": amount,
        "payment_time": payment_time,
        "payment_method": payment_method,
        "category": category,
        "remark": remark if remark else None
    }
    
    storage.create_bill(user.username, bill_data)
    return RedirectResponse(url="/bills", status_code=302)


@app.post("/bills/update/{bill_id}")
async def update_bill(
    request: Request,
    bill_id: int,
    transaction_type: str = Form(...),
    amount: float = Form(...),
    payment_time: str = Form(...),
    payment_method: str = Form(...),
    category: str = Form(...),
    remark: str = Form(default="")
):
    user = require_user(request)
    if user.role == Role.admin:
        raise HTTPException(status_code=403, detail="管理员无法操作账单")
    
    bill_data = {
        "transaction_type": transaction_type,
        "amount": amount,
        "payment_time": payment_time,
        "payment_method": payment_method,
        "category": category,
        "remark": remark if remark else None
    }
    
    result = storage.update_bill(user.username, bill_id, bill_data)
    if not result:
        raise HTTPException(status_code=404, detail="账单不存在")
    
    return RedirectResponse(url="/bills", status_code=302)


@app.post("/bills/delete/{bill_id}")
async def delete_bill(request: Request, bill_id: int):
    user = require_user(request)
    if user.role == Role.admin:
        raise HTTPException(status_code=403, detail="管理员无法操作账单")
    
    result = storage.delete_bill(user.username, bill_id)
    if not result:
        raise HTTPException(status_code=404, detail="账单不存在")
    
    return RedirectResponse(url="/bills", status_code=302)


@app.post("/options/add/payment_method")
async def add_payment_method(request: Request, option_value: str = Form(...)):
    user = require_user(request)
    if not option_value or option_value.strip() == "":
        return RedirectResponse(url="/bills", status_code=302)
    
    storage.add_payment_method(option_value.strip())
    return RedirectResponse(url="/bills", status_code=302)


@app.post("/options/add/category")
async def add_category(request: Request, option_value: str = Form(...)):
    user = require_user(request)
    if not option_value or option_value.strip() == "":
        return RedirectResponse(url="/bills", status_code=302)
    
    storage.add_category(option_value.strip())
    return RedirectResponse(url="/bills", status_code=302)


@app.post("/options/add/time_slot")
async def add_time_slot(request: Request, option_value: str = Form(...)):
    user = require_user(request)
    if not option_value or option_value.strip() == "":
        return RedirectResponse(url="/bills", status_code=302)
    
    storage.add_time_slot(option_value.strip())
    return RedirectResponse(url="/bills", status_code=302)


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    admin = require_admin(request)
    users = storage.get_users()
    users = [u for u in users if u.role != Role.admin]
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "user": admin,
        "users": users
    })


@app.post("/admin/users/create")
async def create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    admin = require_admin(request)
    
    if not username or not password:
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "user": admin,
            "users": storage.get_users(),
            "error": "用户名和密码不能为空"
        })
    
    existing = storage.get_user_by_username(username)
    if existing:
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "user": admin,
            "users": storage.get_users(),
            "error": "用户名已存在"
        })
    
    storage.create_user(username, password)
    return RedirectResponse(url="/admin", status_code=302)


@app.post("/admin/users/delete/{user_id}")
async def delete_user(request: Request, user_id: int):
    admin = require_admin(request)
    
    user = storage.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.role == Role.admin:
        raise HTTPException(status_code=403, detail="无法删除管理员")
    
    storage.delete_user(user_id)
    return RedirectResponse(url="/admin", status_code=302)


@app.post("/admin/users/update/{user_id}")
async def update_user_password(
    request: Request,
    user_id: int,
    new_password: str = Form(...)
):
    admin = require_admin(request)
    
    if not new_password:
        raise HTTPException(status_code=400, detail="密码不能为空")
    
    user = storage.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    storage.update_user_password(user_id, new_password)
    return RedirectResponse(url="/admin", status_code=302)


@app.get("/api/bills")
async def api_get_bills(request: Request, category: str = "全部"):
    user = require_user(request)
    if user.role == Role.admin:
        raise HTTPException(status_code=403, detail="管理员无法访问")
    
    bills = storage.get_bills(user.username, category if category != "全部" else None)
    
    income_total = sum(b.amount for b in bills if b.transaction_type == TransactionType.income)
    expense_total = sum(b.amount for b in bills if b.transaction_type == TransactionType.expense)
    
    return {
        "bills": [
            {
                "id": b.id,
                "transaction_type": b.transaction_type.value,
                "amount": b.amount,
                "payment_time": b.payment_time,
                "payment_method": b.payment_method,
                "category": b.category,
                "remark": b.remark,
                "created_at": b.created_at.strftime("%Y-%m-%d %H:%M:%S")
            }
            for b in bills
        ],
        "income_total": round(income_total, 2),
        "expense_total": round(expense_total, 2),
        "count": len(bills)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
