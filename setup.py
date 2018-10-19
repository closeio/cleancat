import sys
from setuptools import setup

install_requirements = [
    'python-dateutil',
    'pytz',
]
test_requirements = install_requirements + [
    'pytest',
    'coverage',
    'mongoengine',
    'sqlalchemy'
]

if sys.version_info[:2] < (3, 4):
    test_requirements += ['enum34']

setup(
    name='cleancat',
    version='0.7.6',
    url='http://github.com/elasticsales/cleancat',
    license='MIT',
    author='Thomas Steinacher',
    author_email='engineering@close.io',
    maintainer='Thomas Steinacher',
    maintainer_email='engineering@close.io',
    description='Validation library for Python designed to be used with JSON REST frameworks',
    long_description=__doc__,
    packages=[
        'cleancat',
    ],
    zip_safe=False,
    platforms='any',
    install_requires=install_requirements,
    setup_requires=['pytest-runner'],
    test_suite='tests',
    tests_require=test_requirements,
    extras_require={'test': test_requirements},
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
