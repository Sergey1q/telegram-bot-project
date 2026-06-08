"""Управление пользователями (без Jinja2)."""
from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
import os

from bot.database import User, Appointment, Payment
from admin_panel.dependencies import get_db

router = APIRouter(prefix="/users", tags=["users"])


def read_file(filename: str) -> str:
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    filepath = os.path.join(current_dir, "templates", filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def render_page(title: str, content: str) -> str:
    base = read_file("base.html")
    base = base.replace('{% block title %}Админ-панель{% endblock %}', title)
    base = base.replace('{% block content %}{% endblock %}', content)
    base = base.replace('{% block scripts %}{% endblock %}', '')
    return base


@router.get("/", response_class=HTMLResponse)
async def users_list(
    request: Request,
    search: str = None,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db)
):
    """Список пользователей."""
    query = db.query(User)
    
    if search:
        query = query.filter(
            (User.full_name.ilike(f"%{search}%")) |
            (User.username.ilike(f"%{search}%")) |
            (User.phone.ilike(f"%{search}%"))
        )
    
    total = query.count()
    users = query.order_by(User.registered_at.desc()).offset((page - 1) * 20).limit(20).all()
    
    rows_html = ""
    for u in users:
        role_badge = {
            'admin': '<span class="badge bg-danger">Админ</span>',
            'moderator': '<span class="badge bg-warning">Модератор</span>',
        }.get(u.role if isinstance(u.role, str) else u.role.value, '<span class="badge bg-secondary">Пользователь</span>')
        
        status_badge_html = '<span class="badge bg-success">Активен</span>' if not u.is_blocked else '<span class="badge bg-danger">Заблокирован</span>'
        
        rows_html += f"""
        <tr>
            <td>{u.id}</td>
            <td>{u.full_name}</td>
            <td>@{u.username or '—'}</td>
            <td>{u.phone or '—'}</td>
            <td>{role_badge}</td>
            <td>{u.stars_balance} ⭐</td>
            <td>{u.registered_at.strftime('%d.%m.%Y') if u.registered_at else '—'}</td>
            <td>{status_badge_html}</td>
            <td>
                <a href="/users/{u.id}" class="btn btn-sm btn-outline-primary">
                    <i class="bi bi-eye"></i>
                </a>
            </td>
        </tr>"""
    
    if not users:
        rows_html = '<tr><td colspan="9" class="text-center py-4">Нет пользователей</td></tr>'
    
    pages_count = (total + 19) // 20
    pagination_html = ""
    if pages_count > 1:
        for p in range(1, pages_count + 1):
            active = 'active' if p == page else ''
            pagination_html += f'<li class="page-item {active}"><a class="page-link" href="?page={p}&search={search or ""}">{p}</a></li>'
    
    content = f"""
    <div class="container-fluid fade-in">
        <h1 class="mb-4">👥 Пользователи</h1>
        
        <div class="card mb-4">
            <div class="card-body">
                <form method="get" class="row g-3">
                    <div class="col-md-8">
                        <input type="text" name="search" class="form-control" 
                            placeholder="Имя, username, телефон..." value="{search or ''}">
                    </div>
                    <div class="col-md-2">
                        <button type="submit" class="btn btn-primary w-100">🔍 Найти</button>
                    </div>
                </form>
            </div>
        </div>
        
        <div class="card">
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover mb-0">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Пользователь</th>
                                <th>Username</th>
                                <th>Телефон</th>
                                <th>Роль</th>
                                <th>Баланс ⭐</th>
                                <th>Дата</th>
                                <th>Статус</th>
                                <th>Действия</th>
                            </tr>
                        </thead>
                        <tbody>{rows_html}</tbody>
                    </table>
                </div>
            </div>
        </div>
        
        {'<nav class="mt-3"><ul class="pagination justify-content-center">' + pagination_html + '</ul></nav>' if pagination_html else ''}
    </div>"""
    
    return HTMLResponse(content=render_page("Пользователи | Админ-панель", content))


@router.get("/{user_id}", response_class=HTMLResponse)
async def user_detail(request: Request, user_id: int, db: Session = Depends(get_db)):
    """Детали пользователя."""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404)
    
    apps_count = db.query(Appointment).filter(Appointment.user_id == user_id).count()
    payments_sum = db.query(func.sum(Payment.amount_rub)).filter(
        Payment.user_id == user_id, Payment.status == "paid"
    ).scalar() or 0
    
    recent_apps = db.query(Appointment).filter(Appointment.user_id == user_id).order_by(
        Appointment.created_at.desc()
    ).limit(5).all()
    
    apps_rows = ""
    for a in recent_apps:
        apps_rows += f"""
        <tr>
            <td><a href="/appointments/{a.id}">#{a.id}</a></td>
            <td>{a.service_name}</td>
            <td>{a.appointment_date}</td>
            <td>{a.status.value if hasattr(a.status, 'value') else str(a.status)}</td>
            <td>{a.price:.0f}₽</td>
        </tr>"""
    
    if not recent_apps:
        apps_rows = '<tr><td colspan="5" class="text-center">Нет заявок</td></tr>'
    
    status_badge_html = '<span class="badge bg-success">Активен</span>' if not u.is_blocked else '<span class="badge bg-danger">Заблокирован</span>'
    
    content = f"""
    <div class="container-fluid fade-in">
        <nav aria-label="breadcrumb">
            <ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="/dashboard">Дашборд</a></li>
                <li class="breadcrumb-item"><a href="/users">Пользователи</a></li>
                <li class="breadcrumb-item active">{u.full_name}</li>
            </ol>
        </nav>
        
        <div class="row">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body text-center">
                        <div style="font-size: 4rem;">👤</div>
                        <h4>{u.full_name}</h4>
                        <p>@{u.username or 'Нет'}</p>
                        <p>ID: <code>{u.telegram_id}</code></p>
                        <p>{status_badge_html}</p>
                    </div>
                </div>
                
                <div class="card mt-3">
                    <div class="card-header">📊 Статистика</div>
                    <div class="card-body">
                        <p>📅 Заявок: <strong>{apps_count}</strong></p>
                        <p>💰 Потрачено: <strong>{payments_sum:.0f}₽</strong></p>
                        <p>⭐ Баланс звёзд: <strong>{u.stars_balance}</strong></p>
                        <p>📅 Регистрация: {u.registered_at.strftime('%d.%m.%Y') if u.registered_at else '—'}</p>
                    </div>
                </div>
                
                <div class="card mt-3">
                    <div class="card-header">⚡ Действия</div>
                    <div class="card-body d-flex flex-column gap-2">
                        <form method="post" action="/users/{u.id}/block">
                            <button type="submit" class="btn btn-{'success' if u.is_blocked else 'warning'} w-100">
                                {'✅ Разблокировать' if u.is_blocked else '🚫 Заблокировать'}
                            </button>
                        </form>
                        <form method="post" action="/users/{u.id}/role">
                            <select name="role" class="form-select mb-2">
                                <option value="user" {'selected' if str(u.role) == 'user' else ''}>Пользователь</option>
                                <option value="moderator" {'selected' if str(u.role) == 'moderator' else ''}>Модератор</option>
                                <option value="admin" {'selected' if str(u.role) == 'admin' else ''}>Администратор</option>
                            </select>
                            <button type="submit" class="btn btn-primary w-100">Сохранить роль</button>
                        </form>
                    </div>
                </div>
            </div>
            
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header">📋 Последние заявки</div>
                    <div class="card-body p-0">
                        <div class="table-responsive">
                            <table class="table mb-0">
                                <thead>
                                    <tr><th>ID</th><th>Услуга</th><th>Дата</th><th>Статус</th><th>Цена</th></tr>
                                </thead>
                                <tbody>{apps_rows}</tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>"""
    
    return HTMLResponse(content=render_page(f"{u.full_name} | Админ-панель", content))


@router.post("/{user_id}/block")
async def toggle_block(user_id: int, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if u:
        u.is_blocked = not u.is_blocked
        db.commit()
    return RedirectResponse(url=f"/users/{user_id}", status_code=303)


@router.post("/{user_id}/role")
async def change_role(request: Request, user_id: int, db: Session = Depends(get_db)):
    form = await request.form()
    new_role = form.get("role", "user")
    u = db.query(User).filter(User.id == user_id).first()
    if u:
        u.role = new_role
        db.commit()
    return RedirectResponse(url=f"/users/{user_id}", status_code=303)
