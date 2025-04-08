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

from apps.user.views import *
from apps.post.views import *
from apps.category.views import *
from apps.tag.views import *
from apps.dashboard.views import StatsView
from apps.comment.views import CommentViewSet
from apps.upload.views import AvatarUploadView

# 创建路由器
router = DefaultRouter()
router.register(r'blog/posts', PostViewSet, basename='post')

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 认证相关
    path('api/auth/login', LoginView.as_view()),
    path('api/auth/register', RegisterView.as_view()),
    path('api/auth/info', UserInfoView.as_view()),
    path('api/auth/password', ChangePasswordView.as_view()),
    path('api/auth/profile', ProfileUpdateView.as_view()),
    
    # 博客前台API
    path('', include(router.urls)),
    path('blog/posts/hot', HotPostsView.as_view()),
    path('blog/posts/recent', RecentPostsView.as_view()),
    path('api/blog/categories/<int:categoryId>/posts', CategoryPostsView.as_view()),
    path('api/blog/tags/<int:tagId>/posts', TagPostsView.as_view()),
    path('/blog/stats', StatsView.as_view()),
    
    # 后台管理API
    path('api/posts', PostViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('api/posts/<int:pk>', PostViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    })),
    path('api/posts/<int:pk>/adjacent', PostViewSet.as_view({'get': 'adjacent'})),
    path('api/posts/<int:pk>/view', PostViewSet.as_view({'post': 'view'})),
    
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
]

# 添加媒体文件URL
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)