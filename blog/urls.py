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

from apps.user.views import *
from apps.dynamic.views import *
from apps.category.views import *
from apps.tag.views import *
from apps.dashboard.views import StatsView
from apps.comment.views import CommentViewSet
from apps.upload.views import AvatarUploadView, FileUploadView

# 创建路由器
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'dynamics', DynamicViewSet, basename='dynamic')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'comments', CommentViewSet, basename='comment')

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 认证相关
    path('api/auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/info', UserInfoView.as_view()),
    path('api/auth/password', ChangePasswordView.as_view()),
    path('api/auth/profile', ProfileUpdateView.as_view()),
    
    # 博客前台API
    path('api/', include(router.urls)),
    path('blog/dynamics/hot/', HotDynamicsView.as_view({'get': 'list'}), name='hot-dynamics'),
    path('blog/dynamics/recent/', RecentDynamicsView.as_view({'get': 'list'}), name='recent-dynamics'),
    path('blog/categories/', BlogCategoriesView.as_view({'get': 'list'}), name='blog-categories'),
    path('blog/categories/<int:categoryId>/dynamics', CategoryDynamicsView.as_view()),
    path('blog/tags/<int:tagId>/dynamics', TagDynamicsView.as_view()),
    path('blog/stats', StatsView.as_view()),
    
    # 后台管理API
    path('api/stats', StatsView.as_view()),
    path('api/dynamics', DynamicViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('api/dynamics/<int:pk>', DynamicViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    })),
    path('api/dynamics/<int:pk>/adjacent', DynamicViewSet.as_view({'get': 'adjacent'})),
    path('api/dynamics/<int:pk>/view', DynamicViewSet.as_view({'post': 'view'})),
    
    # 其他API
    path('api/categories', CategoryViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('api/categories/<int:pk>', CategoryViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    })),
    path('api/tags', TagViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('api/tags/<int:pk>', TagViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    })),
    path('api/comments', CommentViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('api/comments/<int:pk>', CommentViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    })),
    path('api/upload/avatar', AvatarUploadView.as_view()),
    path('api/upload/file/', FileUploadView.as_view(), name='file-upload'),
]

# 添加媒体文件URL
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)