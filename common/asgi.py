from django.core.asgi import get_asgi_application
from environment.variables import EnvironmentVariable
from environment.base import set_environment

set_environment(EnvironmentVariable.BACKEND_ENVIRONMENT)

asgi_application = get_asgi_application()
