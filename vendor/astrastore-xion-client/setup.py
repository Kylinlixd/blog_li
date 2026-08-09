from setuptools import find_packages, setup


setup(
    name="astrastore-xion-client",
    version="1.1.1",
    description="Vendored AstraStoreXion backend client",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=["requests>=2.25.0", "PyYAML>=5.4.0"],
)
