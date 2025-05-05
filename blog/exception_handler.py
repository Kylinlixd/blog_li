from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import traceback
import re

def custom_exception_handler(exc, context):
    """
    自定义 DRF 异常处理器
    """
    # 先调用 DRF 默认的异常处理器
    response = exception_handler(exc, context)
    
    # 如果已经有处理结果，修改返回格式
    if response is not None:
        error_message = '请求处理失败'
        
        # 处理验证错误
        if hasattr(exc, 'detail'):
            # 处理non_field_errors，直接提取其中的错误信息
            if isinstance(exc.detail, dict) and 'non_field_errors' in exc.detail:
                errors = exc.detail['non_field_errors']
                if isinstance(errors, list) and len(errors) > 0:
                    error_message = str(errors[0])  # 只取第一个错误信息
                else:
                    error_message = str(errors)
            # 处理JWT令牌错误
            elif isinstance(exc.detail, dict) and 'detail' in exc.detail:
                error_message = str(exc.detail['detail'])
            # 处理其他字段错误
            elif isinstance(exc.detail, dict):
                # 获取第一个字段的第一个错误（简洁处理）
                first_field = next(iter(exc.detail))
                errors = exc.detail[first_field]
                if isinstance(errors, list) and len(errors) > 0:
                    error_message = str(errors[0])
                else:
                    error_message = str(errors)
            # 直接使用detail
            else:
                error_message = str(exc.detail)
        
        # 移除错误消息中可能的ErrorDetail前缀
        if "ErrorDetail(" in error_message:
            # 尝试只提取string=''中的内容
            match = re.search(r"string='([^']*)'", error_message)
            if match:
                error_message = match.group(1)
        
        # 返回统一的响应格式
        response_data = {
            'code': response.status_code,
            'message': error_message,
            'data': None
        }
        
        # 在DEBUG模式下添加详细的错误信息
        if settings.DEBUG:
            error_class = exc.__class__.__name__
            error_detail = str(exc)
            error_traceback = traceback.format_exc()
            
            response_data['debug'] = {
                'exception_class': error_class,
                'exception_detail': error_detail,
                'original_response': response.data,  # 保存原始响应
                'traceback': error_traceback.split('\n'),
                'view': context['view'].__class__.__name__ if 'view' in context else None,
                'request_method': context['request'].method if 'request' in context else None,
                'request_path': context['request'].path if 'request' in context else None,
            }
            
        response.data = response_data
    
    return response 