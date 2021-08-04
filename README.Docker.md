# Demo Description for Docker Compose
Execute the following step to start a demo environment using Docker Compose:

**Start the Docker Compose services:**
 ```shell
 docker-compose up
 ```
 Leave this shell instance intact to keep your Docker services running!

# Django Admin
Open your browser at http://localhost:8000/admin to access the Django admin portal:
  * username: `admin`
  * password: `123123`

# MinIO Console
Open your browser at http://localhost:9001 to access the MiniIO Console:
  * username: `minio`
  * password: `minio123`

# docker-compose.yml
Note the following lines in `docker-compose.yml`:
```yaml
 environment:
   GH_MINIO_ENDPOINT: "nginx:9000"
   GH_MINIO_USE_HTTPS: "false"
   GH_MINIO_EXTERNAL_ENDPOINT: "localhost:9000"
   GH_MINIO_EXTERNAL_ENDPOINT_USE_HTTPS: "false"
```

The value of `GH_MINIO_ENDPOINT` is `nginx:9000` because in the used [docker-compose.yml](docker-compose.yml) file the minio instances are load balanced by NGINX.
This means we're not interacting with the four minio1...minio4 instances directly but through the NGINX reverse-proxy.

# Developer Environment
**Input file**: `docker-compose.develop.yml`

If you would like to develop in a Docker Compose environment, execute the following commands:
```shell
docker-compose --project-name "django-minio-backend-DEV" -f docker-compose.develop.yml up -d
docker-compose --project-name "django-minio-backend-DEV" -f docker-compose.develop.yml exec web python manage.py createsuperuser --noinput
docker-compose --project-name "django-minio-backend-DEV" -f docker-compose.develop.yml exec web python manage.py collectstatic --noinput
```
