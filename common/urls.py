from django.contrib import admin
from django.urls import path, include, re_path
from django.conf.urls.static import static
from common import views
from environment.base import STATIC_ROOT, MEDIA_ROOT, MEDIA_URL
from django.views.static import serve
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

urlpatterns = [
                  path('admin/', admin.site.urls),
                  path('', views.HealthView.as_view(), name="Health-Check"),
                  path('api/user/', include(('user.urls', 'user'), namespace='user_management')),
                  path('api/tasks/', include(('tasks.urls', 'tasks'), namespace='tasks')),
                  path('api/token/', TokenObtainPairView.as_view(serializer_class=TokenObtainPairSerializer),
                       name='token_obtain_pair'),
                  path('api/token/refresh/', TokenRefreshView.as_view(serializer_class=TokenObtainPairSerializer),
                       name='token_refresh'),
                  re_path(r'^media/(?P<path>.*)$', serve, {'document_root': MEDIA_ROOT}),
                  re_path(r'^static/(?P<path>.*)$', serve, {'document_root': STATIC_ROOT})
              ] + static(MEDIA_URL, document_root=MEDIA_ROOT)
