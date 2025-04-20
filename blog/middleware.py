from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework import status
from django.urls import resolve
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db import IntegrityError


class APIExceptionMiddleware(MiddlewareMixin):
    """
    全局异常处理中间件
    """
    def process_exception(self, request, exception):
        """
        处理视图函数抛出的异常
        """
        # 只处理API请求
        if not request.path.startswith('/api') and not request.path.startswith('/blog'):
            return None
            
        # 根据异常类型返回不同的错误信息
        if isinstance(exception, ObjectDoesNotExist):
            return JsonResponse({
                'code': status.HTTP_404_NOT_FOUND,
                'message': '请求的资源不存在',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)
            
        elif isinstance(exception, PermissionDenied):
            return JsonResponse({
                'code': status.HTTP_403_FORBIDDEN,
                'message': '没有权限执行此操作',
                'data': None
            }, status=status.HTTP_403_FORBIDDEN)
            
        elif isinstance(exception, IntegrityError):
            return JsonResponse({
                'code': status.HTTP_400_BAD_REQUEST,
                'message': '数据完整性错误，可能存在重复数据',
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)
            
        else:
            # 其他未处理的异常
            return JsonResponse({
                'code': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': '服务器内部错误',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    def process_response(self, request, response):
        """
        处理404错误
        """
        # 只处理API请求的404
        if response.status_code == 404 and (request.path.startswith('/api') or request.path.startswith('/blog')):
            return JsonResponse({
                'code': status.HTTP_404_NOT_FOUND,
                'message': '请求的接口不存在',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)
            
        return response 