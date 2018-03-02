# Onitools

(More or less) the full source code of the [Onitools.moe](https://onitools.moe/) website, for people who want to contribute or host some of the apps themselves. Please keep in mind that this is **mainly a personal project**, for my own practice and learning.

Requires:
* Python 3.5+

Requires, depending on configuration:
* [Redis](https://redis.io/) (for session management)
* MySQL (or another database backend)

Since those are the current defaults I'm using, the respective Python APIs will be installed with the other dependencies. You can change these settings by editing `onitools/default_settings.py`.

To install, clone this repo, and in the root directory run:

```bash
pip3 install .
```

Recommended to do this inside a virtualenv. This should install all the Python dependencies.

Next, create a `settings.cfg` file (it can be placed anywhere) with the following configuration values:

```python
SECRET_KEY = ...
SQLALCHEMY_DATABASE_URI = ...
MAIL_SERVER = ...
MAIL_PORT = ...
MAIL_USE_TLS = ...
MAIL_USE_SSL = ...
MAIL_DEFAULT_SENDER = ...
MAIL_USERNAME = ...
MAIL_PASSWORD = ...
SECURITY_PASSWORD_SALT = ...
```

Most of these configuration values are related to [flask-security](https://pythonhosted.org/Flask-Security/) and its components; you can consult the related docs for their meanings.

Set this configuration file as an environment variable:

```bash
export ONITOOLS_SETTINGS=/path/to/settings.cfg
```

Then you can start the local Flask server:

```bash
python3 onitools/run.py
```
