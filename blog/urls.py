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
from django.http import JsonResponse

from apps.user.views import UserViewSet, CookieTokenRefreshView
from apps.dynamic.views import (
    DynamicViewSet, HotDynamicsView, RecentDynamicsView, 
    CategoryDynamicsView, SearchView, TagDynamicsView
)
from apps.category.views import CategoryViewSet, BlogCategoriesView
from apps.tag.views import TagViewSet
from apps.comment.views import CommentViewSet, BlogCommentView
from apps.upload.views import (
    FileUploadView, AvatarUploadView,
    PublicFileDownloadView, PublicFilePosterDownloadView,
)
from apps.dashboard.views import StatsView
from apps.dashboard.health import SystemHealthView
from apps.access_log.views import AccessLogViewSet, IpSecurityRuleViewSet

# 创建路由器
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'dynamics', DynamicViewSet, basename='dynamic')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'access-logs', AccessLogViewSet, basename='access-log')
router.register(r'access-log-rules', IpSecurityRuleViewSet, basename='access-log-rule')


def hidden_api_root(request):
    return JsonResponse(
        {'code': 404, 'message': '请求的接口不存在', 'data': None},
        status=404,
    )


public_blog_api_patterns = [
    path('dynamics/', DynamicViewSet.as_view({'get': 'list'}), name='api-blog-dynamics'),
    path('dynamics/timeline/', DynamicViewSet.as_view({'get': 'timeline'}), name='api-blog-dynamic-timeline'),
    path('dynamics/hot/', HotDynamicsView.as_view({'get': 'list'}), name='api-hot-dynamics'),
    path('dynamics/recent/', RecentDynamicsView.as_view({'get': 'list'}), name='api-recent-dynamics'),
    path('dynamics/<int:pk>/', DynamicViewSet.as_view({'get': 'retrieve'}), name='api-blog-dynamic-detail'),
    path('dynamics/<int:pk>/adjacent/', DynamicViewSet.as_view({'get': 'adjacent'}), name='api-dynamic-adjacent'),
    path('dynamics/<int:pk>/like/', DynamicViewSet.as_view({'post': 'like'}), name='api-dynamic-like'),
    path('dynamics/<int:pk>/view/', DynamicViewSet.as_view({'put': 'view'}), name='api-dynamic-view'),
    path('comments/', BlogCommentView.as_view(), name='api-blog-comments'),
    path('categories/', BlogCategoriesView.as_view({'get': 'list'}), name='api-blog-categories'),
    path('categories/<int:categoryId>/dynamics/', CategoryDynamicsView.as_view(), name='api-category-dynamics'),
    path('search/', SearchView.as_view(), name='api-blog-search'),
    path('tags/', TagViewSet.as_view({'get': 'list'}), name='api-blog-tags'),
    path('tags/<int:tagId>/dynamics/', TagDynamicsView.as_view(), name='api-tag-dynamics'),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/blog/', include(public_blog_api_patterns)),
    path('api/', hidden_api_root, name='api-root-hidden'),
    path('api/', include(router.urls)),
    
    # 认证相关
    path('api/auth/login/', UserViewSet.as_view({'post': 'login'}), name='login'),
    path('api/auth/register/', UserViewSet.as_view({'post': 'register'}), name='register'),
    path('api/auth/logout/', UserViewSet.as_view({'post': 'logout'}), name='logout'),
    path('api/token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/info/', UserViewSet.as_view({'get': 'info'}), name='user-info'),
    path('api/auth/password/', UserViewSet.as_view({'put': 'password'}), name='change-password'),
    path('api/auth/profile/', UserViewSet.as_view({'put': 'profile'}), name='update-profile'),
    
    # 文件上传API
    path('api/upload/', include('apps.upload.urls')),

    # 公开文件下载（使用脱敏 token，路径中不暴露 upload）
    path('api/files/public/<str:token>/', PublicFileDownloadView.as_view(), name='public-file-download'),
    path('api/files/poster/<str:token>/', PublicFilePosterDownloadView.as_view(), name='public-file-poster'),
    
    # 仪表盘统计API
    path('api/stats/', StatsView.as_view(), name='stats'),
    path('api/system/health/', SystemHealthView.as_view(), name='system-health'),
]

# 开发环境下提供媒体文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
