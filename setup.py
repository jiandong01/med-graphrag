from setuptools import setup, find_packages

setup(
    name="medical-graphrag",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'elasticsearch',
        'pandas',
        'sqlalchemy',
        'mysql-connector-python',
        'python-dotenv',
        'tqdm',
        'huggingface-hub'
    ]
)
