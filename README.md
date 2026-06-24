<div align="center">

![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)
![Aiogram](https://img.shields.io/badge/Aiogram-3.28-green?logo=telegram&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-teal?logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red?logo=sqlalchemy&logoColor=white)
![Telegram Stars](https://img.shields.io/badge/Telegram_Stars-Payments-yellow?logo=telegram&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

# 🤖 Telegram-бот с веб-админкой и Telegram Stars

*Полноценный коммерческий проект для автоматизации бизнеса*

[Демо-бот](https://t.me/Mytest65bot) · [Админ-панель](http://localhost:8000/dashboard) · [Сообщить об ошибке](https://github.com/Sergey1q/telegram-bot-project/issues)

</div>

---

## 📋 Содержание

- [Возможности](#-возможности)
- [Технологии](#-технологии)
- [Скриншоты](#-скриншоты)
- [Быстрый старт](#-быстрый-старт)
- [Структура проекта](#-структура-проекта)
- [Настройка](#-настройка)
- [Для заказчиков](#-для-заказчиков)

---

## 🚀 Возможности

### 🤖 Telegram-бот

| Функция | Описание |
|---------|----------|
| 📅 **Запись на услуги** | Пошаговый процесс: выбор услуги → имя → телефон → дата → время |
| 💰 **Оплата Telegram Stars** | Встроенные платежи Telegram. Тестовый режим (мгновенное подтверждение) |
| ⭐ **Кешбэк** | 5% от суммы платежа возвращается на баланс пользователя |
| 📝 **Отзывы** | Оценка от 1 до 5 звёзд + текстовый комментарий |
| 📊 **Админ-меню** | Просмотр заявок, статистика, управление статусами |
| 📤 **Экспорт в Excel** | Выгрузка заявок в `.xlsx` с форматированием |
| 📢 **Рассылки** | Отправка сообщений всем пользователям бота |
| 👥 **База пользователей** | Автоматическая регистрация при `/start` |

### 🌐 Веб-админка (FastAPI)

| Раздел | Описание |
|--------|----------|
| 📊 **Дашборд** | Карточки статистики, график заявок за 7 дней (Chart.js), последние платежи |
| 📋 **Заявки** | Таблица с фильтрацией по статусу, поиском, пагинацией. Детали заявки, смена статуса |
| 👥 **Пользователи** | Список, поиск, профиль, блокировка, смена роли |
| 🔧 **Услуги** | CRUD: создание, редактирование, удаление. Цена в рублях и Telegram Stars |
| 📢 **Рассылки** | Форма отправки + история рассылок |
| 📤 **Экспорт** | Выгрузка заявок в Excel прямо из браузера |

---

## 🛠 Технологии

| Технология | Версия | Назначение |
|------------|--------|------------|
| **Python** | 3.13 | Язык программирования |
| **Aiogram** | 3.28 | Асинхронный фреймворк для Telegram Bot API |
| **FastAPI** | 0.109 | Веб-фреймворк для админ-панели |
| **Uvicorn** | 0.25 | ASGI-сервер |
| **SQLAlchemy** | 2.0 | ORM для работы с базой данных |
| **SQLite** | — | База данных (через aiosqlite) |
| **Pydantic** | 2.5 | Валидация данных |
| **Pandas** | 2.0 | Формирование Excel-отчётов |
| **OpenPyXL** | 3.1 | Запись `.xlsx` файлов |
| **Chart.js** | 4.x | Интерактивные графики в дашборде |
| **Bootstrap** | 5.3 | Адаптивный UI админ-панели |
| **Jinja2** | 3.1 | Шаблонизация (частично заменена на чистый HTML) |

---

## 📸 Скриншоты

### 🤖 Бот в Telegram

<div align="center">

| Главное меню | Запись на услугу | Оплата Stars |
|:---:|:---:|:---:|
| <img src="https://raw.githubusercontent.com/Sergey1q/telegram-bot-project/main/screenshots/1_start.png" width="250" alt="Главное меню"> | <img src="https://raw.githubusercontent.com/Sergey1q/telegram-bot-project/main/screenshots/2_appointment.png" width="250" alt="Запись"> | <img src="https://raw.githubusercontent.com/Sergey1q/telegram-bot-project/main/screenshots/3_payment.png" width="250" alt="Оплата"> |

</div>

### 🌐 Веб-админка

<div align="center">

| Дашборд | Заявки |
|:---:|:---:|
| <img src="https://raw.githubusercontent.com/Sergey1q/telegram-bot-project/main/screenshots/5_dashboard.png" width="450" alt="Дашборд"> | <img src="https://raw.githubusercontent.com/Sergey1q/telegram-bot-project/main/screenshots/6_dashboard.png" width="450" alt="Заявки"> |

| Экспорт в Excel |
|:---:|
| <img src="https://raw.githubusercontent.com/Sergey1q/telegram-bot-project/main/screenshots/7_excel.png" width="500" alt="Excel"> |

</div>

---

## 📦 Быстрый старт

### 1. Клонируйте репозиторий

```bash
git clone https://github.com/Sergey1q/telegram-bot-project.git
cd telegram-bot-project
