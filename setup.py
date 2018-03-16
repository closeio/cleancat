from setuptools import setup

test_requirements = [
    'nose',
    'coverage',
]

setup(
    name='cleancat',
    version='0.6.0',
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
    test_suite='nose.collector',
    zip_safe=False,
    platforms='any',
    install_requires=[
        'python-dateutil',
    ],
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
