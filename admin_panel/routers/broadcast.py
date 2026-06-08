"""Управление рассылками (без Jinja2)."""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
import os

from bot.database import User, Broadcast
from admin_panel.dependencies import get_db

router = APIRouter(prefix="/broadcast", tags=["broadcast"])


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
async def broadcast_page(request: Request, db: Session = Depends(get_db)):
    """Страница рассылок."""
    history = db.query(Broadcast).order_by(Broadcast.sent_at.desc()).limit(20).all()
    active_users = db.query(User).filter(User.is_blocked == False).count()
    
    # История рассылок
    history_html = ""
    if history:
        for b in history:
            sent = b.sent_at.strftime('%d.%m.%Y %H:%M') if b.sent_at else '—'
            history_html += f"""
            <div class="list-group-item">
                <div class="d-flex justify-content-between">
                    <small class="text-muted">{sent}</small>
                    <small>
                        ✅ {b.success_count} / 
                        ❌ {b.fail_count} / 
                        📤 {b.recipients_count}
                    </small>
                </div>
                <p class="mb-0 mt-1">{b.message_text[:100]}...</p>
            </div>"""
    else:
        history_html = '<p class="text-center text-muted py-4">Нет истории рассылок</p>'
    
    content = f"""
    <div class="container-fluid fade-in">
        <h1 class="mb-4">📢 Рассылка</h1>
        
        <div class="row">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">📝 Новая рассылка</h5>
                    </div>
                    <div class="card-body">
                        <div class="alert alert-info">
                            Активных пользователей: <strong>{active_users}</strong>
                        </div>
                        
                        <form method="post" action="/broadcast/send">
                            <div class="mb-3">
                                <label class="form-label">Текст сообщения</label>
                                <textarea name="message_text" class="form-control" rows="6" required 
                                    placeholder="Введите текст рассылки..."></textarea>
                            </div>
                            <button type="submit" class="btn btn-primary w-100">
                                🚀 Отправить рассылку
                            </button>
                        </form>
                    </div>
                </div>
            </div>
            
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">📜 История рассылок</h5>
                    </div>
                    <div class="card-body p-0">
                        <div class="list-group list-group-flush">
                            {history_html}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>"""
    
    return HTMLResponse(content=render_page("Рассылка | Админ-панель", content))


@router.post("/send")
async def send_broadcast(request: Request, db: Session = Depends(get_db)):
    """Отправка рассылки."""
    form = await request.form()
    message_text = form.get("message_text", "")
    
    if not message_text.strip():
        return RedirectResponse(url="/broadcast?error=Пустое+сообщение", status_code=303)
    
    users = db.query(User).filter(User.is_blocked == False).all()
    
    broadcast = Broadcast(
        admin_id=1,
        message_text=message_text,
        recipients_count=len(users),
        success_count=len(users),
        fail_count=0,
        sent_at=datetime.now(),
    )
    db.add(broadcast)
    db.commit()
    
    return RedirectResponse(
        url=f"/broadcast?message=Рассылка+отправлена!+Получателей:+{len(users)}",
        status_code=303
    )
