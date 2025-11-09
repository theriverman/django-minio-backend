# Docker Compose Description for django-minio-backend
**Hint:** See [CONTRIBUTE.md](CONTRIBUTE.md) for a detailed walkthrough on deploying a demo/development environment.

## Manual Docker Compose Deployment
Execute the following steps to start a demo or development environment using Docker Compose:

**Start the Docker Compose services:**
```shell
docker compose up -d
docker compose exec web uv run manage.py initialize_buckets  # creates the MINIO_STATIC_FILES_BUCKET
docker compose exec web uv run manage.py collectstatic --noinput  # copies static files into MINIO_STATIC_FILES_BUCKET
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
  * username: `minioadmin`
  * password: `minioadmin`
