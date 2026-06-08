"""Pydantic схемы для API."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal

class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    price_rub: float = Field(..., ge=0)
    price_stars: int = Field(0, ge=0)
    duration_minutes: int = Field(60, ge=10)
    category: Optional[str] = None
    is_active: bool = True

class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price_rub: Optional[float] = None
    price_stars: Optional[int] = None
    duration_minutes: Optional[int] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None

class ServiceResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price_rub: float
    price_stars: int
    duration_minutes: int
    is_active: bool
    category: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class AppointmentUpdate(BaseModel):
    status: Optional[str] = None
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    appointment_date: Optional[str] = None
    appointment_time: Optional[str] = None
    comment: Optional[str] = None

class BroadcastCreate(BaseModel):
    message_text: str = Field(..., min_length=1, max_length=4096)

class UserResponse(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str]
    full_name: str
    phone: Optional[str]
    email: Optional[str]
    role: str
    stars_balance: int
    total_spent: float
    is_blocked: bool
    registered_at: datetime
    last_active: datetime
    
    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_users: int
    total_appointments: int
    total_payments: int
    total_services: int
    new_users_today: int
    new_appointments: int
    monthly_revenue: float
