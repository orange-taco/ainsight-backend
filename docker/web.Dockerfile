FROM python:3.11-slim

LABEL maintainer="oscar2272"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /src

COPY ./src /src
COPY ./requirements /requirements

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*


ARG DEV=true

RUN pip install --upgrade pip && \
    pip install -r /requirements/web.txt && \
    if [ "$DEV" = "true" ] ; then \
        pip install -r /requirements/web.dev.txt ; \
    fi

# 앱 코드 복사

# 포트 오픈
EXPOSE 8000

# default command
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
