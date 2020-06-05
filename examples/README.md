Django Minio Backend - Example
------------------------------

You can find a reference implementation of an attachment app using **django-minio-backend** as its storage backend.

To simplify testing this library, you can hook this reference implementation 
into a dummy project very quickly by executing the following steps:

**Note:** It is implied you have already created a virtualenv and installed Django via `pip install Django`.

1. Create a new Django application:
```bash
django-admin startproject storagetest
``` 

2. Clone this library:
```bash
git clone https://github.com/theriverman/django-minio-backend.git
```

3. Copy `django-minio-backend` into your newly created sandbox application's root:
```bash
cp -R django-minio-backend storagetest/django-minio-backend
```

4. Copy `django-minio-backend/examples/Attachments` into your newly created sandbox application's root:
```bash
cp -R django-minio-backend/examples/Attachments storagetest/Attachments
```

5. Add the applications to the `INSTALLED_APPS` list:
```python
INSTALLED_APPS = [
    # ...
    'django_minio_backend',  # Storage backend
    'Attachments',  # Reference app
]
```

6. Create & Execute migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

7. Edit `settings.py`, then start Django and play around in the admin panel.
