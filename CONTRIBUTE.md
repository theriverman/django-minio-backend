# Contributing to Django Minio Backend

You can find a reference implementation of a Django app using **django-minio-backend** as a storage backend in
[DjangoExampleApplication/models.py](DjangoExampleApplication/models.py).

When you're finished with your changes, please open a pull request!

## Development Environment

This project uses [uv](https://docs.astral.sh/uv/) for fast and reliable dependency management. If you don't have `uv` installed, you can install it with:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

### Super Quick Setup (Recommended)

Get [make](https://www.gnu.org/software/make/) for your OS:
* [Linux](https://www.gnu.org/distros/distros.html)
* [macOS](https://formulae.brew.sh/formula/make)
* [Windows](https://gnuwin32.sourceforge.net/packages/make.htm)

Choose between deploying locally or with Docker Compose:
* `make local`    - uses the public play.min.io instance
* `make compose`  - uses a locally deployed MinIO stack

Should you make changes to the models, you can execute `makemigrations` then `migrate` in a single step:
* `make migrations`

## Quick Setup with Docker Compose
See [CONTRIBUTE.Docker.md](./CONTRIBUTE.Docker.md).

### Quick Setup with Local Deployment

Execute the following steps:

```bash
# Clone the repository
git clone https://github.com/theriverman/django-minio-backend.git
cd django-minio-backend

# Install dependencies and set up the environment
uv sync

# Run migrations
uv run python manage.py migrate

# Create admin account (optional)
uv run python manage.py createsuperuser

# Run the development server
uv run python manage.py runserver
```

That's it! `uv sync` automatically creates a virtual environment and installs all dependencies.

### Alternative Setup (Traditional)

If you prefer traditional virtual environments:

```bash
# Clone the repository
git clone https://github.com/theriverman/django-minio-backend.git
cd django-minio-backend

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies with uv (much faster than pip)
uv pip install -r requirements.txt

# Or use pip if you prefer
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create admin account (optional)
python manage.py createsuperuser

# Run the development server
python manage.py runserver
```

## Testing

Testing happens against a real MinIO server.
If you're running the tests locally, make sure you have a MinIO server running available at `127.0.0.1:9000`.
See [MinIO Setup](#MinIO-Setup) for more details.

Run the test suite with:

```bash
# With uv
uv run python manage.py test
```

**Note:** Tests are quite minimal at the moment. Contributions to improve test coverage are welcome!

## MinIO Setup

The tests require a running MinIO instance. You can start one with Docker:

```bash
docker run -p 9000:9000 -d \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  minio/minio server /data
```

## Making Changes

1. Create a new branch for your feature or bugfix
2. Make your changes
3. Run tests to ensure nothing breaks
4. Update documentation if needed
5. Open a pull request with a clear description of your changes

## Code Style

Please follow [PEP 8](https://peps.python.org/pep-0008/) guidelines and ensure your code is well-documented.

## Questions?

If you have questions or need help, feel free to open an issue on GitHub!
