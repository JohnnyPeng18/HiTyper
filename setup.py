from setuptools import setup
from os import path, environ
from hityper import __version__


setup(
    name = "hityper",
    version = __version__,
    description = "HiTyper: A hybrid type inference framework for Python",
    long_description = open(path.join(path.abspath(path.dirname(__file__)), "README.md"), "r", encoding = "utf-8").read(),
    long_description_content_type='text/markdown',
    url = "https://github.com/JohnnyPeng18/HiTyper",
    author = "Yun Peng",
    author_email = "research@yunpeng.work",
    classifiers = [
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Software Development :: Build Tools"
    ],
    keywords = ["python", "type inference", "static analysis"],
    packages = ["hityper"],
    python_requries='>=3.9',
    install_requires = open(path.join(path.abspath(path.dirname(__file__)), "requirements.txt"), "r", encoding = "utf-8").read().splitlines(),
    entry_points={
        'console_scripts': [
            'hityper = hityper.__main__:main'
        ]
    }
)