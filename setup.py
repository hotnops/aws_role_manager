from setuptools import setup, find_packages
setup(
    name='awsrolemanager',
    version = '0.0.1',
    license = 'bsd3-clause-clear',
    description = 'A tool for quickly managing AWS roles',
    author = 'hotnops',
    author_email = 'hotnops@protonmail.com',
    url = 'https://github.com/hotnops/aws_role_manager',
    download_url = '',
    packages=['awsrolemanager'],
    install_requires=[
        'prettytable',
        'termcolor',
        'wcwidth'
    ],
    scripts = ['bin/awsrolemanager']
    
)