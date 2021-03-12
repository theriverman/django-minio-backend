import os
from datetime import datetime
from setuptools import find_packages, setup

from version import get_git_version

with open("README.md", "r") as readme_file:
    long_description = readme_file.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))


setup(
    name='django-minio-backend',
    version=get_git_version(),
    packages=find_packages(),
    include_package_data=True,
    license=f'MIT License | Copyright (c) {datetime.now().year} Kristof Daja',
    description='The django-minio-backend provides a wrapper around the MinIO Python Library.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/theriverman/django-minio-backend',
    author='Kristof Daja (theriverman)',
    author_email='kristof@daja.hu',
    install_requires=[
        'Django>=2.2.2',
        'minio>=7.0.2'
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 2.2',
        'Framework :: Django :: 3.0',
        'Framework :: Django :: 3.1',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: Content Management System',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
    ],
)
