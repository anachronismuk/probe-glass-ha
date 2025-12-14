FROM python:3.11-alpine
RUN apk update && apk add shadow
RUN groupadd -g 1234 probe && useradd -m -u 1234 -g probe probe
RUN mkdir /usr/src/app && chown probe /usr/src/app
USER probe
WORKDIR /usr/src/app
COPY ./requirements.txt .
RUN pip install -r requirements.txt
ENV PYTHONUNBUFFERED=1
COPY . .