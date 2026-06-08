"""Модели базы данных."""
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import enum

from bot.config import config

# Синхронный движок для админ-панели
sync_engine = create_engine(
    config.database_url.replace("sqlite+aiosqlite:///", "sqlite:///"),
    echo=False
)

# Асинхронный движок для бота
if "sqlite" in config.database_url:
    async_engine = create_async_engine(
        config.database_url.replace("sqlite:///", "sqlite+aiosqlite:///"),
        echo=False
    )
else:
    async_engine = create_async_engine(config.database_url, echo=False)

AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"

class AppointmentStatus(str, enum.Enum):
    NEW = "new"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    REFUNDED = "refunded"
    EXPIRED = "expired"

class User(Base):
    """Пользователь бота."""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=True)
    full_name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    email: Mapped[str] = mapped_column(String(100), nullable=True)
    role: Mapped[UserRole] = mapped_column(String(20), default=UserRole.USER)
    stars_balance: Mapped[int] = mapped_column(Integer, default=0)  # Баланс звёзд
    total_spent: Mapped[float] = mapped_column(Float, default=0.0)  # Всего потрачено
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_active: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    appointments = relationship("Appointment", back_populates="user")
    payments = relationship("Payment", back_populates="user")

class Service(Base):
    """Услуги."""
    __tablename__ = "services"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    price_rub: Mapped[float] = mapped_column(Float, default=0)
    price_stars: Mapped[int] = mapped_column(Integer, default=0)  # Цена в Telegram Stars
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    category: Mapped[str] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    appointments = relationship("Appointment", back_populates="service")

class Appointment(Base):
    """Запись на услугу."""
    __tablename__ = "appointments"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), nullable=True)
    service_name: Mapped[str] = mapped_column(String(200))
    client_name: Mapped[str] = mapped_column(String(100))
    client_phone: Mapped[str] = mapped_column(String(20))
    client_email: Mapped[str] = mapped_column(String(100), nullable=True)
    appointment_date: Mapped[str] = mapped_column(String(20))
    appointment_time: Mapped[str] = mapped_column(String(10))
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[AppointmentStatus] = mapped_column(String(20), default=AppointmentStatus.NEW)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    payment_method: Mapped[str] = mapped_column(String(20), nullable=True)  # 'stars' или 'cash'
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    user = relationship("User", back_populates="appointments")
    service = relationship("Service", back_populates="appointments")

class Payment(Base):
    """Платежи через Telegram Stars."""
    __tablename__ = "payments"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id"), nullable=True)
    telegram_payment_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=True)
    amount_stars: Mapped[int] = mapped_column(Integer)
    amount_rub: Mapped[float] = mapped_column(Float)
    status: Mapped[PaymentStatus] = mapped_column(String(20), default=PaymentStatus.PENDING)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    payload: Mapped[str] = mapped_column(Text, nullable=True)  # JSON с данными заказа
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    paid_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="payments")

class Broadcast(Base):
    """История рассылок."""
    __tablename__ = "broadcasts"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    admin_id: Mapped[int] = mapped_column(Integer)
    message_text: Mapped[str] = mapped_column(Text)
    recipients_count: Mapped[int] = mapped_column(Integer)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

class Feedback(Base):
    """Отзывы."""
    __tablename__ = "feedbacks"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)
    rating: Mapped[int] = mapped_column(Integer, nullable=True)  # 1-5
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    user = relationship("User")

# Создаём таблицы
Base.metadata.create_all(sync_engine)
