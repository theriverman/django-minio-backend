Contributing to Django Minio Backend
====================================

You can find a reference implementation of a Django app using **django-minio-backend-five** as a storage backend in
[DjangoExampleApplication/models.py](DjangoExampleApplication/models.py).

When you're finished with your changes, please open a pull request!

Development Environment
-----------------------

Execute the following steps to prepare your development environment:

1. Clone the library:

    ```bash
    git clone https://github.com/theriverman/django-minio-backend.git
    cd django-minio-backend
    ```

2. Create a virtual environment and activate it:

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3. Install Python Dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4. Execute Django Migrations:

    ```bash
    python manage.py migrate
    ```

5. Create Admin Account (optional):

    ```bash
    python manage.py createsuperuser
    ```

6. Run the Project:

    ```bash
    python manage.py runserver
    ```

Testing
-------

You can run tests by executing the following command (in the repository root):

```bash
python manage.py test
```

**Note:** Tests are quite poor at the moment.
