from setuptools import setup

with open('README.txt') as f:
    long_description = f.read()

setup(
    name='gorillaml',
    version='dev-1.0.0',
    packages=['gorillaml',],
    license='Creative Commons Attribution-Noncommercial-Share Alike license',
    long_description=long_description,
    author='Washim Ahmed',
    author_email='washim.ahmed@gmail.com',
    python_requires='>=3',
    scripts=['bin/gorillaml-canvas', 'bin/gorillaml-config']
)