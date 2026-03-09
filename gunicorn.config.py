"""
Deployment Gunicorn config file
"""
import multiprocessing
from environment.variables import EnvironmentVariable

# WSGI file package of the project
wsgi_app = 'common.wsgi'

# The Socket to be bind
bind = f'0.0.0.0:{EnvironmentVariable.BACKEND_PORT}'

# The number of worker processes for handling requests
workers = multiprocessing.cpu_count()

# The number of worker threads for handling requests
threads = (2 * workers) + 1

# Workers silent for more than this many seconds are killed and restarted
timeout = 60
