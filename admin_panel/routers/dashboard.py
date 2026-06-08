"""Дашборд админ-панели (чистый HTML, без Jinja2)."""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import json
import os

from bot.database import User, Appointment, Payment, Service
from admin_panel.dependencies import get_db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def read_file(filename: str) -> str:
    """Читает файл из папки templates."""
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    filepath = os.path.join(current_dir, "templates", filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def render_dashboard(
    total_users: int,
    total_appointments: int,
    total_payments: int,
    total_services: int,
    new_users_today: int,
    new_appointments: int,
    monthly_revenue: float,
    appointments_rows: str,
    payments_cards: str,
    chart_labels: list,
    chart_data: list,
) -> str:
    """Рендерит HTML дашборда."""
    
    # Читаем base.html
    base = read_file("base.html")
    
    # Контент дашборда
    content = f"""
    <div class="container-fluid fade-in">
        <h1 class="mb-4">📊 Дашборд</h1>
        
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card bg-primary text-white stat-card">
                    <div class="card-body">
                        <h5 class="card-title">👥 Пользователи</h5>
                        <h2>{total_users}</h2>
                        <small>+{new_users_today} сегодня</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-warning text-dark stat-card">
                    <div class="card-body">
                        <h5 class="card-title">📅 Заявки</h5>
                        <h2>{total_appointments}</h2>
                        <small>{new_appointments} новых</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-success text-white stat-card">
                    <div class="card-body">
                        <h5 class="card-title">💰 Платежи</h5>
                        <h2>{total_payments}</h2>
                        <small>{int(monthly_revenue)} ₽ за месяц</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-info text-white stat-card">
                    <div class="card-body">
                        <h5 class="card-title">🔧 Услуги</h5>
                        <h2>{total_services}</h2>
                        <small>активных</small>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-md-8">
                <div class="card mb-4">
                    <div class="card-header">📈 Заявки за 7 дней</div>
                    <div class="card-body">
                        <canvas id="appointmentsChart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="col-md-4">
                <div class="card mb-4">
                    <div class="card-header">💳 Последние платежи</div>
                    <div class="card-body">
                        {payments_cards}
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">📋 Последние заявки</div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-striped mb-0">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Клиент</th>
                                <th>Услуга</th>
                                <th>Дата</th>
                                <th>Статус</th>
                                <th>Оплата</th>
                            </tr>
                        </thead>
                        <tbody>
                            {appointments_rows}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
    document.addEventListener('DOMContentLoaded', function() {{
        var ctx = document.getElementById('appointmentsChart');
        if (ctx) {{
            new Chart(ctx.getContext('2d'), {{
                type: 'line',
                data: {{
                    labels: {json.dumps(chart_labels)},
                    datasets: [{{
                        label: 'Заявки',
                        data: {json.dumps(chart_data)},
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.3,
                        fill: true,
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{ legend: {{ display: false }} }},
                    scales: {{
                        y: {{ beginAtZero: true, ticks: {{ stepSize: 1 }} }}
                    }}
                }}
            }});
        }}
    }});
    </script>
    """
    
    # Вставляем контент и скрипты в base.html
    # Заменяем placeholder'ы
    result = base.replace(
        '{% block content %}{% endblock %}',
        content
    )
    result = result.replace(
        '{% block scripts %}{% endblock %}',
        ''
    )
    result = result.replace('{% block title %}Админ-панель{% endblock %}', 'Дашборд | Админ-панель')
    
    return result


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Главная страница дашборда."""
    
    # Статистика
    total_users = db.query(User).count()
    total_appointments = db.query(Appointment).count()
    total_payments = db.query(Payment).filter(Payment.status == "paid").count()
    total_services = db.query(Service).count()
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    new_users_today = db.query(User).filter(User.registered_at >= today).count()
    new_appointments = db.query(Appointment).filter(Appointment.status == "new").count()
    
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_revenue = db.query(func.sum(Payment.amount_rub)).filter(
        Payment.status == "paid",
        Payment.paid_at >= month_start
    ).scalar() or 0
    
    # Заявки → HTML строки
    recent_apps = db.query(Appointment).order_by(Appointment.created_at.desc()).limit(5).all()
    appointments_rows = ""
    for app in recent_apps:
        status_str = app.status.value if hasattr(app.status, 'value') else str(app.status)
        if 'new' in status_str.lower():
            badge = '<span class="badge bg-warning">🆕 Новая</span>'
        elif 'confirmed' in status_str.lower():
            badge = '<span class="badge bg-success">✅ Подтверждена</span>'
        elif 'completed' in status_str.lower():
            badge = '<span class="badge bg-info">✔️ Выполнена</span>'
        elif 'cancelled' in status_str.lower():
            badge = '<span class="badge bg-danger">❌ Отменена</span>'
        else:
            badge = f'<span class="badge bg-secondary">{status_str}</span>'
        
        paid = "✅" if app.is_paid else "❌"
        
        appointments_rows += f"""
        <tr>
            <td><strong>#{app.id}</strong></td>
            <td>{app.client_name}</td>
            <td>{app.service_name}</td>
            <td>{app.appointment_date} {app.appointment_time}</td>
            <td>{badge}</td>
            <td>{paid}</td>
        </tr>"""
    
    if not recent_apps:
        appointments_rows = """
        <tr>
            <td colspan="6" class="text-center py-4 text-muted">
                <p>Заявок пока нет</p>
            </td>
        </tr>"""
    
    # Платежи → HTML строки
    recent_pays = db.query(Payment).filter(Payment.status == "paid").order_by(
        Payment.paid_at.desc()
    ).limit(5).all()
    payments_cards = ""
    for pay in recent_pays:
        paid_at = pay.paid_at.strftime('%d.%m %H:%M') if pay.paid_at else '—'
        desc = (pay.description or '')[:50]
        payments_cards += f"""
        <div class="mb-2 p-2 border rounded">
            <strong>{pay.amount_stars} ⭐</strong>
            <small class="text-muted float-end">{paid_at}</small>
            <br><small>{desc}</small>
        </div>"""
    
    if not recent_pays:
        payments_cards = '<p class="text-muted">Нет платежей</p>'
    
    # Данные для графика
    chart_labels = []
    chart_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        next_day = day + timedelta(days=1)
        count = db.query(Appointment).filter(
            Appointment.created_at >= day,
            Appointment.created_at < next_day
        ).count()
        chart_labels.append(day.strftime("%d.%m"))
        chart_data.append(count)
    
    # Рендерим
    html = render_dashboard(
        total_users=total_users,
        total_appointments=total_appointments,
        total_payments=total_payments,
        total_services=total_services,
        new_users_today=new_users_today,
        new_appointments=new_appointments,
        monthly_revenue=monthly_revenue,
        appointments_rows=appointments_rows,
        payments_cards=payments_cards,
        chart_labels=chart_labels,
        chart_data=chart_data,
    )
    
    return HTMLResponse(content=html)
