from setuptools import setup, find_packages

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name="hey",
    version="0.1",
    author="Zhifeng Jiang",
    author_email="zjiangaj@connect.ust.hk",
    description="'Hey' is your command-line agent.",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/SamuelGong/hey",
    license="Apache 2.0",
    packages=find_packages(exclude=("log", "examples", "rdb")),
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "hey=quick_start:main",  # Maps 'hey' command to cli.py:main()
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    keywords="AI, LLMs, Large Language Models, Agent, OS, Operating System, Terminal",
    python_requires='>=3.10',
)
