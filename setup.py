import io
import re

from setuptools import setup
from os.path import join, dirname


def requirements(dev=False):
    name = 'dev-requirements.txt' if dev else 'requirements.txt'
    with open(join(dirname(__file__), name), 'r') as f:
        return f.readlines()


VERSION_FILE = "cleancat/__init__.py"
with io.open(VERSION_FILE, "rt", encoding="utf8") as f:
    version = re.search(r'__version__ = ([\'"])(.*?)\1', f.read()).group(2)


setup(
    name='cleancat',
    version=version,
    url='http://github.com/elasticsales/cleancat',
    license='MIT',
    author='Thomas Steinacher',
    author_email='engineering@close.io',
    maintainer='Thomas Steinacher',
    maintainer_email='engineering@close.io',
    description='Validation library for Python designed to be used with JSON REST frameworks',
    long_description=__doc__,
    packages=['cleancat'],
    zip_safe=False,
    platforms='any',
    install_requires=requirements(),
    setup_requires=['pytest-runner'],
    test_suite='tests',
    tests_require=requirements() + requirements(dev=True),
    extras_require={'test': requirements(dev=True)},
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
