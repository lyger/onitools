from setuptools import setup

dependencies = [
    'flask',
    'flask-mail',
    'flask-restful',
    'flask-sqlalchemy',
    'flask-sessionstore',
    'flask-security',
    'flask-socketio',
    'flask-uploads',
    'flask-wtf',
    'bcrypt',
    'dynet',
    'eventlet',
    'mysqlclient',
    'redis'
]

setup(
    name='onitools',
    packages=['onitools'],
    version='0.1.1',
    include_package_data=True,
    install_requires=dependencies
)
