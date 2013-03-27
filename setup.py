from setuptools import setup

# Stops exit traceback on tests
try:
    import multiprocessing
except:
   pass

setup(
    name='cleancat',
    version='0.2',
    url='http://github.com/elasticsales/cleancat',
    license='BSD',
    author='Thomas Steinacher',
    author_email='cleancat@thomasst.ch',
    maintainer='Thomas Steinacher',
    maintainer_email='cleancat@thomasst.ch',
    description='Validation library for Python designed to be used with JSON REST frameworks',
    long_description=__doc__,
    packages=[
        'cleancat',
    ],
    test_suite='nose.collector',
    zip_safe=False,
    platforms='any',
    setup_requires=[
        'nose',
        'coverage',
        'python-dateutil',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
