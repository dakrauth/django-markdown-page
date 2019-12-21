#!/usr/bin/env python
import os, sys
from setuptools import setup, find_packages

if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit(0)

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
    install_requires=['django-taggit', 'choice_enum', 'markdown2'],
    classifiers=(
        'Environment :: Web Environment',
        'Framework :: Django',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
    ),
    packages=find_packages(),
    package_data={'mdpage': ['templates/mdpage/*']},
)
