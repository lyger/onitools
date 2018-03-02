from setuptools import setup

dependencies = [
    'flask',
    'flask-mail',
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
    include_package_data=True,
    install_requires=dependencies
)
