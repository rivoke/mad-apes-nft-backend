import requests
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from common.utils import CommonUtils

class HealthView(APIView):
    permission_classes = (AllowAny,)

    def get(self, _):
        return CommonUtils.dispatch_success("SUCCESS")


