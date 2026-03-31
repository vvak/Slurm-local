from setuptools import setup, find_packages

setup(
    name="slurm-local",
    version="1.0.0",
    description="Spin up a local Docker-based SLURM cluster for testing",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "docker>=6.0.0",
    ],
    entry_points={
        "console_scripts": [
            "slurm-local=slurm_cluster.cli:main",
        ],
    },
    include_package_data=True,
)
