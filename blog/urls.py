"""
URL configuration for blog project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.user.views import UserViewSet, CustomTokenObtainPairView
from apps.dynamic.views import DynamicViewSet, HotDynamicsView, RecentDynamicsView
from apps.category.views import CategoryViewSet, BlogCategoriesView
from apps.tag.views import TagViewSet
from apps.comment.views import CommentViewSet
from apps.upload.views import FileUploadView
from apps.dashboard.views import StatsView

# 创建路由器
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'dynamics', DynamicViewSet, basename='dynamic')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'comments', CommentViewSet, basename='comment')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    
    # 认证相关
    path('api/auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/info/', UserViewSet.as_view({'get': 'info'}), name='user-info'),
    path('api/auth/password/', UserViewSet.as_view({'put': 'password'}), name='change-password'),
    path('api/auth/profile/', UserViewSet.as_view({'put': 'profile'}), name='update-profile'),
    
    # 博客前台API
    path('blog/dynamics/hot/', HotDynamicsView.as_view({'get': 'list'}), name='hot-dynamics'),
    path('blog/dynamics/recent/', RecentDynamicsView.as_view({'get': 'list'}), name='recent-dynamics'),
    path('blog/categories/', BlogCategoriesView.as_view({'get': 'list'}), name='blog-categories'),
    
    # 文件上传API
    path('api/upload/file/', FileUploadView.as_view(), name='file-upload'),
    
    # 仪表盘统计API
    path('api/stats/', StatsView.as_view(), name='stats'),
]

# 添加媒体文件URL
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)