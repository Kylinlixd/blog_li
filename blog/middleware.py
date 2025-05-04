from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework import status
from django.urls import resolve
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db import IntegrityError
from django.conf import settings
import traceback


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
            
        # 获取异常的详细信息
        error_class = exception.__class__.__name__
        error_detail = str(exception)
        error_traceback = traceback.format_exc()
            
        # 根据异常类型返回不同的错误信息
        if isinstance(exception, ObjectDoesNotExist):
            response_data = {
                'code': status.HTTP_404_NOT_FOUND,
                'message': '请求的资源不存在',
                'data': None
            }
            
        elif isinstance(exception, PermissionDenied):
            response_data = {
                'code': status.HTTP_403_FORBIDDEN,
                'message': '没有权限执行此操作',
                'data': None
            }
            
        elif isinstance(exception, IntegrityError):
            response_data = {
                'code': status.HTTP_400_BAD_REQUEST,
                'message': '数据完整性错误，可能存在重复数据',
                'data': None
            }
            
        else:
            # 其他未处理的异常
            response_data = {
                'code': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': '服务器内部错误',
                'data': None
            }
            
        # 在DEBUG模式下，添加详细的错误信息
        if settings.DEBUG:
            response_data['debug'] = {
                'exception_class': error_class,
                'exception_detail': error_detail,
                'traceback': error_traceback.split('\n')
            }
            
        if isinstance(exception, ObjectDoesNotExist):
            return JsonResponse(response_data, status=status.HTTP_404_NOT_FOUND)
        elif isinstance(exception, PermissionDenied):
            return JsonResponse(response_data, status=status.HTTP_403_FORBIDDEN)
        elif isinstance(exception, IntegrityError):
            return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
        else:
            return JsonResponse(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    def process_response(self, request, response):
        """
        处理404错误
        """
        # 只处理API请求的404
        if response.status_code == 404 and (request.path.startswith('/api') or request.path.startswith('/blog')):
            response_data = {
                'code': status.HTTP_404_NOT_FOUND,
                'message': '请求的接口不存在',
                'data': None
            }
            
            # 在DEBUG模式下，添加更多信息
            if settings.DEBUG:
                response_data['debug'] = {
                    'path': request.path,
                    'method': request.method,
                    'GET': dict(request.GET),
                    'POST': dict(request.POST) if request.method == 'POST' else None
                }
                
            return JsonResponse(response_data, status=status.HTTP_404_NOT_FOUND)
            
        return response 