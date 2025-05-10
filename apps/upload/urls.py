from django.urls import path
from .views import FileUploadView, AvatarUploadView

urlpatterns = [
    path('', FileUploadView.as_view(), name='file-upload'),
    path('avatar/', AvatarUploadView.as_view(), name='avatar-upload'),
] 