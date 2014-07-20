from setuptools import setup
from setuptools import find_packages

with open("README.rst") as f:
    long_desc = f.read()


setup(
    name="rpckit",
    version="0.1.0",
    description="",
    long_description=long_desc,
    author="Isman Firmansyah",
    author_email="isman.firmansyah@gmail.com",
    url="https://bitbucket.org/iromli/rpckit",
    packages=find_packages(),
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
    ],
    zip_safe=False,
    install_requires=[
        "pyzmq",
        "msgpack-python",
    ],
)
