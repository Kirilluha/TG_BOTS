# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем необходимые пакеты для сборки и зависимости
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        build-essential \
        libffi-dev \
        libssl-dev \
        zlib1g-dev \
        libjpeg62-turbo-dev \
        libjpeg62-turbo \ 
        libpng-dev \
        libtiff-dev \
        iputils-ping && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


# Создаём рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .

# Обновляем pip
RUN pip install --upgrade pip

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Очищаем ненужные пакеты после установки зависимостей
RUN apt-get purge -y --auto-remove \
        gcc \
        build-essential \
        libffi-dev \
        libssl-dev \
        zlib1g-dev \
        libjpeg62-turbo-dev \
        libpng-dev \
        libtiff-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


# Указываем команду для запуска бота
CMD ["python", "main.py"]