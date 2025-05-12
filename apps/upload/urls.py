from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FileUploadView, AvatarUploadView,
    FileManagementViewSet, FileCategoryViewSet,
    FileTagViewSet
)

router = DefaultRouter()
router.register(r'files', FileManagementViewSet)
router.register(r'categories', FileCategoryViewSet)
router.register(r'tags', FileTagViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('upload/', FileUploadView.as_view(), name='file-upload'),
    path('avatar/', AvatarUploadView.as_view(), name='avatar-upload'),
] 