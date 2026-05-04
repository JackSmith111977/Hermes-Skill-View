from setuptools import setup, find_packages

setup(
    name="sra-agent",
    version="1.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pyyaml>=5.1",
    ],
    extras_require={
        "dev": ["pytest>=7.0", "pytest-benchmark>=4.0"],
    },
    entry_points={
        "console_scripts": [
            "sra=skill_advisor.cli:main",
        ],
    },
    python_requires=">=3.8",
)
