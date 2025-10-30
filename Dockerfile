FROM python:3.11-alpine

RUN apk add --no-cache build-base sqlite-dev \
    && rm -rf /var/cache/apk/*

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt \
    && apk del build-base sqlite-dev \
    && rm /app/requirements.txt

COPY . /app/

VOLUME /app/jellyseerr_bot.db

ENV TELEGRAM_API_ID= \
    TELEGRAM_API_HASH= \
    TELEGRAM_BOT_TOKEN= \
    JELLYSEERR_URL= \
    JELLYSEERR_API_KEY= \
    JELLYFIN_URL= \
    JELLYFIN_API_KEY= \
    ADMIN_USER_IDS= \
    DB_PATH="jellyseerr_bot.db"

CMD ["python", "main.py"]