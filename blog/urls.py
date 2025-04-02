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
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView

from apps.user.views import *
from apps.post.views import *
from apps.category.views import *
from apps.tag.views import *
from apps.dashboard.views import StatsView
from apps.comment.views import CommentViewSet
from apps.upload.views import AvatarUploadView


urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 认证相关
    path('api/auth/login', LoginView.as_view()),
    path('api/auth/register', RegisterView.as_view()),
    path('api/auth/info', UserInfoView.as_view()),
    path('api/auth/password', ChangePasswordView.as_view()),
    path('api/auth/profile', ProfileUpdateView.as_view()),
    
    # 文章管理
    path('api/posts', PostViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('api/posts/<int:pk>', PostViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    })),
    path('api/posts/recent', RecentPostsView.as_view()),
    
    # 分类管理
    path('api/categories', CategoryViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('api/categories/<int:pk>', CategoryViewSet.as_view({
        'put': 'update',
        'delete': 'destroy'
    })),
    
    # 标签管理
    path('api/tags', TagViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('api/tags/<int:pk>', TagViewSet.as_view({
        'put': 'update',
        'delete': 'destroy'
    })),
    
    # 评论管理
    path('api/comments', CommentViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('api/comments/<int:pk>', CommentViewSet.as_view({
        'delete': 'destroy'
    })),
    path('api/comments/<int:pk>/approve', CommentViewSet.as_view({
        'put': 'approve'
    })),
    path('api/comments/<int:pk>/reject', CommentViewSet.as_view({
        'put': 'reject'
    })),
    
    # 文件上传
    path('api/upload/avatar', AvatarUploadView.as_view()),
    
    # 仪表盘
    path('api/stats', StatsView.as_view()),
    
    # Token刷新
    path('api/token/refresh', TokenRefreshView.as_view()),
]

# 添加媒体文件URL
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)