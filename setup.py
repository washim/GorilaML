from setuptools import setup

with open('README.txt') as f:
    long_description = f.read()

setup(
    name='gorillaml',
    version='0.0.4',
    packages=['gorillaml'],
    license='MIT license',
    url="https://www.gorillaml.com",
    long_description=long_description,
    author='Washim Ahmed',
    author_email='washim.ahmed@gmail.com',
    python_requires='>=3',
    include_package_data=True,
    install_requires=[
        'Flask>=1.1.1',
        'Flask-WTF>=0.14.2',
        'WTForms>=2.2.1',
        'Werkzeug>=0.15.5',
        'Flask-Cors>=3.0.8',
        'SQLAlchemy>=1.3.6',
        'click>=7.0',
        'watchdog>=0.9.0',
        'beautifulsoup4>=4.8.0',
        'requests>=2.22.0',
        'mpld3>=0.3'
    ],
    entry_points={
        'console_scripts': [
            'gorillaml-canvas=gorillaml:cli',
            'gorillaml-forever=gorillaml:start_server'
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    ]
)
