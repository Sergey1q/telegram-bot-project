"""Управление заявками (без Jinja2)."""
from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import pandas as pd
import io
import os

from bot.database import Appointment, AppointmentStatus, User, Payment
from admin_panel.dependencies import get_db

router = APIRouter(prefix="/appointments", tags=["appointments"])


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


def status_badge(status_str: str) -> str:
    status_str = status_str.lower() if hasattr(status_str, 'lower') else str(status_str).lower()
    if 'new' in status_str:
        return '<span class="badge bg-warning">🆕 Новая</span>'
    elif 'confirmed' in status_str:
        return '<span class="badge bg-success">✅ Подтверждена</span>'
    elif 'completed' in status_str:
        return '<span class="badge bg-info">✔️ Выполнена</span>'
    elif 'cancelled' in status_str:
        return '<span class="badge bg-danger">❌ Отменена</span>'
    return f'<span class="badge bg-secondary">{status_str}</span>'


@router.get("/", response_class=HTMLResponse)
async def appointments_list(
    request: Request,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db)
):
    """Список заявок с фильтрацией."""
    query = db.query(Appointment)
    
    if status and status != "all":
        query = query.filter(Appointment.status == status)
    
    if search:
        query = query.filter(
            (Appointment.client_name.ilike(f"%{search}%")) |
            (Appointment.client_phone.ilike(f"%{search}%")) |
            (Appointment.service_name.ilike(f"%{search}%"))
        )
    
    total = query.count()
    apps = query.order_by(Appointment.created_at.desc()).offset((page - 1) * 20).limit(20).all()
    
    # Счётчики статусов
    status_counts = {
        "all": db.query(Appointment).count(),
        "new": db.query(Appointment).filter(Appointment.status == AppointmentStatus.NEW).count(),
        "confirmed": db.query(Appointment).filter(Appointment.status == AppointmentStatus.CONFIRMED).count(),
        "completed": db.query(Appointment).filter(Appointment.status == AppointmentStatus.COMPLETED).count(),
        "cancelled": db.query(Appointment).filter(Appointment.status == AppointmentStatus.CANCELLED).count(),
    }
    
    # Строки таблицы
    rows_html = ""
    if apps:
        for app in apps:
            status_str = app.status.value if hasattr(app.status, 'value') else str(app.status)
            paid = "✅" if app.is_paid else "❌"
            rows_html += f"""
            <tr>
                <td><strong>#{app.id}</strong></td>
                <td>{app.client_name}</td>
                <td>{app.client_phone}</td>
                <td>{app.service_name}</td>
                <td>{app.appointment_date} {app.appointment_time}</td>
                <td>{app.price:.0f}₽</td>
                <td>{status_badge(status_str)}</td>
                <td>{paid}</td>
                <td>
                    <a href="/appointments/{app.id}" class="btn btn-sm btn-outline-primary">
                        <i class="bi bi-eye"></i>
                    </a>
                </td>
            </tr>"""
    else:
        rows_html = """
        <tr>
            <td colspan="9" class="text-center py-4 text-muted">
                <p>Заявок не найдено</p>
            </td>
        </tr>"""
    
    # Пагинация
    pages_count = (total + 19) // 20
    pagination_html = ""
    if pages_count > 1:
        for p in range(1, pages_count + 1):
            active = 'active' if p == page else ''
            pagination_html += f"""
            <li class="page-item {active}">
                <a class="page-link" href="?page={p}&status={status or 'all'}&search={search or ''}">{p}</a>
            </li>"""
    
    content = f"""
    <div class="container-fluid fade-in">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1>📋 Заявки</h1>
            <a href="/appointments/export/excel" class="btn btn-success">
                <i class="bi bi-download"></i> Экспорт Excel
            </a>
        </div>
        
        <div class="card mb-4">
            <div class="card-body">
                <form method="get" class="row g-3">
                    <div class="col-md-3">
                        <label class="form-label">Статус</label>
                        <select name="status" class="form-select" onchange="this.form.submit()">
                            <option value="all">Все ({status_counts['all']})</option>
                            <option value="new">Новые ({status_counts['new']})</option>
                            <option value="confirmed">Подтверждённые ({status_counts['confirmed']})</option>
                            <option value="completed">Выполненные ({status_counts['completed']})</option>
                            <option value="cancelled">Отменённые ({status_counts['cancelled']})</option>
                        </select>
                    </div>
                    <div class="col-md-5">
                        <label class="form-label">Поиск</label>
                        <input type="text" name="search" class="form-control" 
                            placeholder="Имя, телефон, услуга..." value="{search or ''}">
                    </div>
                    <div class="col-md-2 d-flex align-items-end">
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
                                <th>Клиент</th>
                                <th>Телефон</th>
                                <th>Услуга</th>
                                <th>Дата</th>
                                <th>Цена</th>
                                <th>Статус</th>
                                <th>Оплата</th>
                                <th>Действия</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        {'<nav class="mt-3"><ul class="pagination justify-content-center">' + pagination_html + '</ul></nav>' if pagination_html else ''}
    </div>"""
    
    return HTMLResponse(content=render_page("Заявки | Админ-панель", content))


@router.get("/export/excel")
async def export_appointments_excel(db: Session = Depends(get_db)):
    """Экспорт заявок в Excel."""
    apps = db.query(Appointment).order_by(Appointment.created_at.desc()).all()
    
    data = [{
        'ID': a.id,
        'Клиент': a.client_name,
        'Телефон': a.client_phone,
        'Услуга': a.service_name,
        'Дата': a.appointment_date,
        'Время': a.appointment_time,
        'Цена': a.price,
        'Оплачено': 'Да' if a.is_paid else 'Нет',
        'Статус': a.status.value if hasattr(a.status, 'value') else str(a.status),
        'Комментарий': a.comment or '',
    } for a in apps]
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Заявки', index=False)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=appointments_{datetime.now().strftime('%Y%m%d')}.xlsx"}
    )


@router.get("/{appointment_id}", response_class=HTMLResponse)
async def appointment_detail(request: Request, appointment_id: int, db: Session = Depends(get_db)):
    """Детали заявки."""
    app = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not app:
        raise HTTPException(status_code=404)
    
    status_str = app.status.value if hasattr(app.status, 'value') else str(app.status)
    paid = f"✅ {app.payment_method}" if app.is_paid else "❌ Не оплачено"
    
    content = f"""
    <div class="container-fluid fade-in">
        <nav aria-label="breadcrumb">
            <ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="/dashboard">Дашборд</a></li>
                <li class="breadcrumb-item"><a href="/appointments">Заявки</a></li>
                <li class="breadcrumb-item active">#{app.id}</li>
            </ol>
        </nav>
        
        <div class="row">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header d-flex justify-content-between">
                        <h5 class="mb-0">📋 Заявка #{app.id}</h5>
                        {status_badge(status_str)}
                    </div>
                    <div class="card-body">
                        <div class="row mb-3">
                            <div class="col-md-6"><strong>Услуга:</strong> {app.service_name}</div>
                            <div class="col-md-6"><strong>Стоимость:</strong> {app.price:.0f}₽</div>
                        </div>
                        <div class="row mb-3">
                            <div class="col-md-6"><strong>Клиент:</strong> {app.client_name}</div>
                            <div class="col-md-6"><strong>Телефон:</strong> {app.client_phone}</div>
                        </div>
                        <div class="row mb-3">
                            <div class="col-md-6"><strong>Дата:</strong> {app.appointment_date}</div>
                            <div class="col-md-6"><strong>Время:</strong> {app.appointment_time}</div>
                        </div>
                        <div class="row mb-3">
                            <div class="col-md-6"><strong>Оплата:</strong> {paid}</div>
                            <div class="col-md-6"><strong>Комментарий:</strong> {app.comment or 'Нет'}</div>
                        </div>
                    </div>
                </div>
                
                <div class="card mt-3">
                    <div class="card-header"><h5 class="mb-0">⚡ Действия</h5></div>
                    <div class="card-body d-flex gap-2">
                        <form method="post" action="/appointments/{app.id}/status">
                            <input type="hidden" name="status" value="confirmed">
                            <button class="btn btn-success">✅ Подтвердить</button>
                        </form>
                        <form method="post" action="/appointments/{app.id}/status">
                            <input type="hidden" name="status" value="completed">
                            <button class="btn btn-info">✔️ Выполнено</button>
                        </form>
                        <form method="post" action="/appointments/{app.id}/status">
                            <input type="hidden" name="status" value="cancelled">
                            <button class="btn btn-danger">❌ Отменить</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>"""
    
    return HTMLResponse(content=render_page(f"Заявка #{app.id} | Админ-панель", content))


@router.post("/{appointment_id}/status")
async def update_status(request: Request, appointment_id: int, db: Session = Depends(get_db)):
    """Обновление статуса."""
    form = await request.form()
    new_status = form.get("status")
    
    app = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if app and new_status:
        app.status = new_status
        app.updated_at = datetime.now()
        db.commit()
    
    return RedirectResponse(url=f"/appointments/{appointment_id}", status_code=303)
