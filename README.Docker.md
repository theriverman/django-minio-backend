# Docker Compose Description for django-minio-backend
Execute the following step to start a demo environment using Docker Compose:

**Start the Docker Compose services:**
 ```shell
docker compose up -d
docker compose exec web python manage.py createsuperuser --noinput
docker compose exec web python manage.py collectstatic --noinput
 ```

## About docker-compose.yml
Note the following lines in `docker-compose.yml`:
```yaml
environment:
  GH_MINIO_ENDPOINT: "nginx:9000"
  GH_MINIO_USE_HTTPS: "false"
  GH_MINIO_EXTERNAL_ENDPOINT: "localhost:9000"
  GH_MINIO_EXTERNAL_ENDPOINT_USE_HTTPS: "false"
```

MinIO is load balanced by nginx, so all connections made from Django towards MinIO happens through the internal `nginx` FQDN. <br>
Therefore, the value of `GH_MINIO_ENDPOINT` is `nginx:9000`.

# Web Access
Both Django(:8000) and MinIO(:9001) expose a Web GUI and their ports are mapped to the host machine.

## Django Admin
Open your browser at http://localhost:8000/admin to access the Django admin portal:
  * username: `admin`
  * password: `123123`

## MinIO Console
Open your browser at http://localhost:9001 to access the MiniIO Console:
  * username: `minio`
  * password: `minio123`

# Developer Environment
An alternative docker-compose file is available for **django-minio-backend** which does not copy the source files into the container, but maps them as a volume.
**Input file**: `docker-compose.develop.yml`

If you would like to develop in a Docker Compose environment, execute the following commands:
```shell
docker compose -f docker-compose.develop.yml up -d
docker compose -f docker-compose.develop.yml exec web python manage.py createsuperuser --noinput
docker compose -f docker-compose.develop.yml exec web python manage.py collectstatic --noinput
```
