#!/bin/bash
# Lilysana Education 🌸 — Скрипт швидкого запуску
# Переходимо в директорію бекенду
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/backend"

echo "🌸 Запуск Lilysana Education..."

# Перевірка наявності віртуального середовища
if [ ! -d ".venv" ]; then
    echo "Створюю віртуальне оточення..."
    python3.12 -m venv .venv || python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
fi

# Запуск сервера та бота
echo "🚀 Сервер стартує на http://localhost:8000"
echo "🤖 Бот підключається до Telegram (@LilysanaTestAndRest_bot)..."
.venv/bin/python3 run.py
