import os
import datetime
from setuptools import find_packages, setup

with open("README.md", "r") as readme_file:
    long_description = readme_file.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

CURRENT_GIT_TAG = 'v2.5.0'
year = datetime.datetime.now().year

print(f'setup.py :: Using git tag {CURRENT_GIT_TAG}')

setup(
    name='django-minio-backend',
    version=CURRENT_GIT_TAG,
    packages=find_packages(),
    include_package_data=True,
    license=f'MIT License | Copyright (c) {year} Kristof Daja',
    description='The django-minio-backend provides a wrapper around the MinIO Python Library.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/theriverman/django-minio-backend',
    author='Kristof Daja (theriverman)',
    author_email='kristof@daja.hu',
    install_requires=[
        'Django>=2.2.2',
        'minio>=4.0.9,<7'
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 2.0',
        'Framework :: Django :: 2.1',
        'Framework :: Django :: 2.2',
        'Framework :: Django :: 3.0',
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
