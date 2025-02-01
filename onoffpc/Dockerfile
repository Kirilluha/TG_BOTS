# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем необходимые пакеты для сборки и ping
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        build-essential \
        libffi-dev \
        libssl-dev \
        iputils-ping && \
    rm -rf /var/lib/apt/lists/*

# Создаём рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .
#COPY .env .


# Обновляем pip до последней версии
RUN pip install --upgrade pip

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код бота
#COPY prog.py .

# Удаляем инструменты сборки, чтобы уменьшить размер образа
RUN apt-get purge -y --auto-remove gcc build-essential libffi-dev libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# Указываем команду для запуска бота
CMD ["python", "prog.py"]
