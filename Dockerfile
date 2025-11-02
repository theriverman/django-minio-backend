# syntax=docker/dockerfile:1
FROM python:3.14-slim-trixie

MAINTAINER theriverman

ENV PYTHONUNBUFFERED=1
WORKDIR /code

# Dummy version for uv
ARG SETUPTOOLS_SCM_PRETEND_VERSION=0.0.1
ENV SETUPTOOLS_SCM_PRETEND_VERSION=0.0.1

# Copy Demo Project - it'll get overriden by Docker Compose later on
COPY ./manage.py /code/manage.py
COPY ./django_minio_backend /code/django_minio_backend
COPY ./DjangoExampleProject /code/DjangoExampleProject
COPY ./DjangoExampleApplication /code/DjangoExampleApplication
COPY ./.python-version /code/.python-version
COPY ./pyproject.toml /code/pyproject.toml
COPY ./uv.lock /code/uv.lock
COPY ./README.md /code/README.md

# Install Python Packages
RUN pip install --upgrade pip
RUN pip install uv
RUN uv sync

# Execute initial migrations
RUN uv run manage.py migrate

# Create the default super user
ARG DJANGO_SUPERUSER_USERNAME="admin"
ARG DJANGO_SUPERUSER_PASSWORD="123123"
ARG DJANGO_SUPERUSER_EMAIL="admin@local.test"
RUN uv run manage.py createsuperuser --noinput

# Port
EXPOSE 8000/tcp

# Default startup method for the image
CMD ["uv", "run", "manage.py","runserver", "0.0.0.0:8000"]
