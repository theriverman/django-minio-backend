# syntax=docker/dockerfile:1
FROM python:3
ENV PYTHONUNBUFFERED=1
WORKDIR /code

# Copy Demo Project
COPY ./manage.py /code/manage.py
COPY ./django_minio_backend /code/django_minio_backend
COPY ./DjangoExampleProject /code/DjangoExampleProject
COPY ./DjangoExampleApplication /code/DjangoExampleApplication

# Copy and install requirements.txt
COPY requirements.txt /code/
RUN pip install -r /code/requirements.txt
