#!/usr/bin/env python
import os, sys
from setuptools import setup, find_packages


with open('README.rst') as f:
    long_description = f.read()


VERSION = __import__('mdpage').get_version()

setup(
    name='django-markdown-page',
    version=VERSION,
    url='https://github.com/dakrauth/django-markdown-page',
    author='David A Krauth',
    author_email='dakrauth@gmail.com',
    description='Easily generate and publish web pages via Markdown.',
    long_description=long_description,
    platforms=['any'],
    license='MIT License',
    install_requires=['django-taggit', 'choice_enum', 'markdown2', 'django-bootstrap5'],
    classifiers=(
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 3.2',
        'Framework :: Django :: 4.0',
        'Framework :: Django :: 4.1',
        'Framework :: Django :: 4.2',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Utilities',
    ),
    packages=find_packages(),
    package_data={'mdpage': ['templates/mdpage/*']},
)
