from setuptools import setup, find_packages

setup(
    name="xray-sdk",
    version="0.1.0",
    description="X-Ray SDK for debugging multi-step algorithmic systems",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "pydantic>=2.5.0",
    ],
    python_requires=">=3.8",
)