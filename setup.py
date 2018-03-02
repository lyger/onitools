from setuptools import setup

setup(
    name='onitools',
    packages=['onitools'],
    include_package_data=True,
    install_requires=['flask', 'flask-sqlalchemy', 'flask-session',
                      'flask-security', 'flask-socketio', 'bcrypt', 'dynet']
)
