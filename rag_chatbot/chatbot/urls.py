from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.conf import settings
from django.conf.urls.static import static
from .views import RegisterView, WhoAmIView, DocumentUploadView, QueryView

urlpatterns = [
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('auth/me/', WhoAmIView.as_view(), name='auth_me'),
    path('documents/upload/', DocumentUploadView.as_view(), name='documents_upload'),
    path('query/', QueryView.as_view(), name='rag_query'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)