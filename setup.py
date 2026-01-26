from setuptools import setup, find_packages

setup(
    name="sentry-one-bot",
    version="12.0.0",
    packages=find_packages(),
    install_requires=[
        "Flask>=2.3.3",
        "requests>=2.31.0",
        "python-telegram-bot>=20.3",
    ],
    extras_require={
        "quantum": ["qiskit>=1.0.0", "qiskit-ibm-runtime>=0.21.0", "qiskit-aer>=0.12.0"],
        "ai": ["numpy>=1.24.0"],
        "scheduler": ["APScheduler>=3.10.4"],
    },
    python_requires=">=3.8",
)