from setuptools import setup

with open('README.rst') as f:
    long_description = f.read()

setup(
    name='gorillaml',
    version='0.1.2',
    packages=['gorillaml'],
    license='MIT license',
    url="https://www.gorillaml.com",
    description='This is the application which allow individual, organization, developer, publisher to manage, '
                'publish, monitor webservices, machine learning api, custom forms and many more active '
                'development very easily.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Washim Ahmed',
    author_email='washim.ahmed@gmail.com',
    python_requires='>=3',
    include_package_data=True,
    install_requires=[
        'Flask',
        'Flask-WTF',
        'WTForms',
        'Werkzeug',
        'Flask-Cors',
        'SQLAlchemy',
        'click',
        'watchdog',
        'beautifulsoup4',
        'requests',
        'mpld3',
        'scipy',
        'pandas',
        'matplotlib',
        'PyQt5<5.13'
    ],
    entry_points={
        'console_scripts': [
            'gorillaml-canvas=gorillaml:cli'
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    ]
)
