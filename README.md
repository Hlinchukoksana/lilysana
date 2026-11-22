# 🌸 Lilysana Education — MVP 2.0

Telegram-бот + Mini App для підготовки до НМТ та проходження освітніх курсів.

---

## 📂 Структура проєкту

```
lilysana/
├── backend/              # Python FastAPI + Aiogram
│   ├── app/
│   │   ├── api/          # REST API роутери
│   │   ├── bot_handlers/ # Aiogram хендлери
│   │   ├── models/       # SQLAlchemy ORM моделі
│   │   ├── services/     # Бізнес-логіка
│   │   ├── config.py     # Конфігурація
│   │   ├── database.py   # DB сесії
│   │   └── main.py       # FastAPI app
│   ├── tests/            # Pytest тести
│   ├── run.py            # Єдина точка запуску
│   ├── requirements.txt
│   └── .env.example
└── frontend/             # Telegram Mini App
    ├── index.html
    ├── css/style.css
    └── js/
        ├── api.js        # API клієнт
        ├── app.js        # Роутер і ініціалізація
        ├── components/   # Компоненти UI
        └── pages/        # Сторінки
```

---

## 🚀 Запуск

### 1. Налаштування середовища

```bash
cd backend
cp .env.example .env
# Відредагуй .env — вкажи BOT_TOKEN
```

### 2. Встановлення залежностей

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Запуск бекенду

```bash
python run.py
```

Сервер стартує на `http://localhost:8000`.  
Swagger UI: `http://localhost:8000/docs`

### 4. Запуск фронтенду

Для локального тестування (поза Telegram):

```bash
cd frontend
python3 -m http.server 3000
# Відкрий http://localhost:3000
```

> **DEV_MODE**: коли `BOT_TOKEN` встановлено та `DEV_MODE=true` у `.env`,  
> аутентифікація через initData пропускається — зручно для локальної розробки.

### 5. Підключення до Telegram

1. Зареєструй бота через [@BotFather](https://t.me/BotFather)
2. Вкажи `BOT_TOKEN` у `.env`
3. Задеплой фронтенд на HTTPS (наприклад, через [ngrok](https://ngrok.com/))
4. Налаштуй Mini App URL у BotFather: `Manage Bot → Bot Settings → Menu Button → URL`

---

## 🧪 Тести

```bash
cd backend
pytest -v
```

Тести покривають:
- Реєстрацію та онбординг користувача
- НМТ теми, тести, результати, логіку повторень
- Курси: створення, генерацію розкладу, ліміти, прогрес
- Безпеку: HMAC-SHA256 верифікацію initData

---

## ⚙️ Змінні середовища (`.env`)

| Змінна | Опис | Приклад |
|--------|------|---------|
| `BOT_TOKEN` | Токен Telegram-бота | `123456:ABCdef...` |
| `DATABASE_URL` | SQLite або PostgreSQL URL | `sqlite+aiosqlite:///./lilysana.db` |
| `DEV_MODE` | Вимкнути перевірку initData | `true` |
| `WEBHOOK_URL` | URL для webhook (опційно) | `https://example.com` |

---

## 🏗 Технології

**Backend:**
- FastAPI + Uvicorn
- Aiogram 3 (Telegram Bot)
- SQLAlchemy (async) + aiosqlite
- APScheduler (нагадування)
- Pydantic Settings

**Frontend:**
- Telegram Web App SDK
- Vanilla JS (ES6+)
- CSS Custom Properties (design system)
- SVG Charts (без зовнішніх залежностей)

---

## 📱 Функціонал Mini App

| Сторінка | Функції |
|----------|---------|
| 🏠 Головна | Привітання, статистика тижня, найближчі заняття |
| 🎯 НМТ | Предмети → Теми → Тести → Результати → Графік → Повторення |
| 🎓 Курси | Список курсів, деталі, сесії, прогрес, ручний % |
| 📅 Розклад | Всі заняття + НМТ-повторення, згруповані по датах |
| 📊 Статистика | Години, виконання, НМТ бали, серія |
| ⚙️ Налаштування | Модулі, ліміти, сповіщення |

---

## 🤖 Telegram-бот

| Команда | Дія |
|---------|-----|
| `/start` | Вітання + вибір часу на навчання + кнопка Mini App |
| Нагадування | Автоматично за розкладом через APScheduler |
