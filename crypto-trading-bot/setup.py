from setuptools import setup, find_packages

setup(
    name="crypto-trading-bot",
    version="1.0.0",
    description="Cryptocurrency trading bot with CCXT, multiple strategies, and backtesting engine",
    author="Rishu",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "ccxt>=4.0.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "ta>=0.11.0",
        "matplotlib>=3.7.0",
        "flask>=3.0.0",
        "pyyaml>=6.0",
        "rich>=13.0.0",
        "tabulate>=0.9.0",
    ],
    entry_points={
        "console_scripts": [
            "cryptobot=main:main",
        ],
    },
)
