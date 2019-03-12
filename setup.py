from setuptools import find_packages, setup

setup(
    name='katy',
    version='0.1',
    description='Command line tools for CaTE',
    author='Noel Lee',
    author_email='kyl116@ic.ac.uk',
    license='MIT',
    packages=find_packages(),
    install_requires=[
        'requests',
        'beautifulsoup4',
        'pypdf2',
    ],
    scripts=[
        'scripts/cate_download.py',
        'scripts/rename_chapters.py',
    ],
)
