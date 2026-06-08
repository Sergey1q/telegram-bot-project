"""Управление услугами (без Jinja2)."""
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
import os

from bot.database import Service, Appointment
from admin_panel.dependencies import get_db

router = APIRouter(prefix="/services", tags=["services"])


def read_file(filename: str) -> str:
    """Читает HTML-шаблон из папки templates."""
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    filepath = os.path.join(current_dir, "templates", filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def render_page(title: str, content: str) -> str:
    """Вставляет контент в base.html."""
    base = read_file("base.html")
    base = base.replace('{% block title %}Админ-панель{% endblock %}', title)
    base = base.replace('{% block content %}{% endblock %}', content)
    base = base.replace('{% block scripts %}{% endblock %}', '')
    return base


@router.get("/", response_class=HTMLResponse)
async def services_list(request: Request, db: Session = Depends(get_db)):
    """Список услуг."""
    services = db.query(Service).order_by(Service.created_at.desc()).all()
    
    # Генерируем HTML карточек услуг
    cards_html = ""
    for s in services:
        active_badge = '' if s.is_active else '<span class="badge bg-secondary">Не активна</span>'
        description = (s.description or 'Нет описания')[:100]
        category_badge = f'<span class="badge bg-info">{s.category}</span>' if s.category else ''
        
        cards_html += f"""
        <div class="col-md-4 mb-4">
            <div class="card h-100 {'opacity-50' if not s.is_active else ''}">
                <div class="card-body">
                    <div class="d-flex justify-content-between">
                        <h5 class="card-title">{s.name}</h5>
                        {active_badge}
                    </div>
                    <p class="text-muted">{description}</p>
                    <hr>
                    <div class="row">
                        <div class="col-6">
                            <strong>💰 Цена:</strong><br>
                            {s.price_rub:.0f}₽
                        </div>
                        <div class="col-6">
                            <strong>⭐ Звёзды:</strong><br>
                            {s.price_stars} ⭐
                        </div>
                    </div>
                    <div class="mt-2">
                        <strong>⏱ Длительность:</strong> {s.duration_minutes} мин
                    </div>
                    {category_badge}
                </div>
                <div class="card-footer d-flex gap-2">
                    <a href="/services/{s.id}/edit" class="btn btn-sm btn-outline-primary flex-grow-1">
                        ✏️ Редактировать
                    </a>
                    <form method="post" action="/services/{s.id}/delete" class="flex-grow-1">
                        <button type="submit" class="btn btn-sm btn-outline-danger w-100" onclick="return confirm('Удалить услугу?')">
                            🗑 Удалить
                        </button>
                    </form>
                </div>
            </div>
        </div>"""
    
    if not services:
        cards_html = """
        <div class="col-12 text-center py-5">
            <i class="bi bi-inbox" style="font-size: 3rem;"></i>
            <h4 class="mt-3">Нет услуг</h4>
            <a href="/services/add" class="btn btn-primary mt-2">Добавить первую услугу</a>
        </div>"""
    
    content = f"""
    <div class="container-fluid fade-in">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1>🔧 Услуги</h1>
            <a href="/services/add" class="btn btn-primary">
                <i class="bi bi-plus-lg"></i> Добавить услугу
            </a>
        </div>
        <div class="row">
            {cards_html}
        </div>
    </div>"""
    
    return HTMLResponse(content=render_page("Услуги | Админ-панель", content))


@router.get("/add", response_class=HTMLResponse)
async def add_service_form(request: Request):
    """Форма добавления услуги."""
    content = f"""
    <div class="container fade-in" style="max-width: 600px;">
        <h1 class="mb-4">➕ Добавление услуги</h1>
        <div class="card">
            <div class="card-body">
                <form method="post" action="/services/add">
                    <div class="mb-3">
                        <label class="form-label">Название *</label>
                        <input type="text" name="name" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Описание</label>
                        <textarea name="description" class="form-control" rows="3"></textarea>
                    </div>
                    <div class="row mb-3">
                        <div class="col-md-4">
                            <label class="form-label">Цена (₽) *</label>
                            <input type="number" name="price_rub" class="form-control" required value="0" min="0">
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">Цена (⭐)</label>
                            <input type="number" name="price_stars" class="form-control" value="0" min="0">
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">Длит. (мин)</label>
                            <input type="number" name="duration_minutes" class="form-control" value="60" min="10">
                        </div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Категория</label>
                        <input type="text" name="category" class="form-control">
                    </div>
                    <div class="mb-3 form-check">
                        <input type="checkbox" name="is_active" class="form-check-input" id="is_active" checked>
                        <label class="form-check-label" for="is_active">Услуга активна</label>
                    </div>
                    <div class="d-flex gap-2">
                        <button type="submit" class="btn btn-primary">➕ Добавить</button>
                        <a href="/services" class="btn btn-outline-secondary">Отмена</a>
                    </div>
                </form>
            </div>
        </div>
    </div>"""
    
    return HTMLResponse(content=render_page("Добавление услуги | Админ-панель", content))


@router.post("/add")
async def add_service(request: Request, db: Session = Depends(get_db)):
    """Добавление услуги."""
    form = await request.form()
    
    service = Service(
        name=form.get("name"),
        description=form.get("description"),
        price_rub=float(form.get("price_rub", 0)),
        price_stars=int(form.get("price_stars", 0)),
        duration_minutes=int(form.get("duration_minutes", 60)),
        category=form.get("category"),
        is_active=form.get("is_active") == "on",
    )
    db.add(service)
    db.commit()
    
    return RedirectResponse(url="/services", status_code=303)


@router.get("/{service_id}/edit", response_class=HTMLResponse)
async def edit_service_form(request: Request, service_id: int, db: Session = Depends(get_db)):
    """Форма редактирования услуги."""
    s = db.query(Service).filter(Service.id == service_id).first()
    if not s:
        raise HTTPException(status_code=404)
    
    checked = 'checked' if s.is_active else ''
    
    content = f"""
    <div class="container fade-in" style="max-width: 600px;">
        <h1 class="mb-4">✏️ Редактирование услуги</h1>
        <div class="card">
            <div class="card-body">
                <form method="post" action="/services/{s.id}/edit">
                    <div class="mb-3">
                        <label class="form-label">Название *</label>
                        <input type="text" name="name" class="form-control" required value="{s.name}">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Описание</label>
                        <textarea name="description" class="form-control" rows="3">{s.description or ''}</textarea>
                    </div>
                    <div class="row mb-3">
                        <div class="col-md-4">
                            <label class="form-label">Цена (₽) *</label>
                            <input type="number" name="price_rub" class="form-control" required value="{s.price_rub:.0f}" min="0">
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">Цена (⭐)</label>
                            <input type="number" name="price_stars" class="form-control" value="{s.price_stars}" min="0">
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">Длит. (мин)</label>
                            <input type="number" name="duration_minutes" class="form-control" value="{s.duration_minutes}" min="10">
                        </div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Категория</label>
                        <input type="text" name="category" class="form-control" value="{s.category or ''}">
                    </div>
                    <div class="mb-3 form-check">
                        <input type="checkbox" name="is_active" class="form-check-input" id="is_active" {checked}>
                        <label class="form-check-label" for="is_active">Услуга активна</label>
                    </div>
                    <div class="d-flex gap-2">
                        <button type="submit" class="btn btn-primary">💾 Сохранить</button>
                        <a href="/services" class="btn btn-outline-secondary">Отмена</a>
                    </div>
                </form>
            </div>
        </div>
    </div>"""
    
    return HTMLResponse(content=render_page("Редактирование услуги | Админ-панель", content))


@router.post("/{service_id}/edit")
async def update_service(request: Request, service_id: int, db: Session = Depends(get_db)):
    """Обновление услуги."""
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404)
    
    form = await request.form()
    
    service.name = form.get("name", service.name)
    service.description = form.get("description", service.description)
    service.price_rub = float(form.get("price_rub", service.price_rub))
    service.price_stars = int(form.get("price_stars", service.price_stars))
    service.duration_minutes = int(form.get("duration_minutes", service.duration_minutes))
    service.category = form.get("category", service.category)
    service.is_active = form.get("is_active") == "on"
    
    db.commit()
    return RedirectResponse(url="/services", status_code=303)


@router.post("/{service_id}/delete")
async def delete_service(service_id: int, db: Session = Depends(get_db)):
    """Удаление услуги."""
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404)
    
    has_appointments = db.query(Appointment).filter(Appointment.service_id == service_id).count()
    if has_appointments:
        service.is_active = False
        db.commit()
    else:
        db.delete(service)
        db.commit()
    
    return RedirectResponse(url="/services", status_code=303)
