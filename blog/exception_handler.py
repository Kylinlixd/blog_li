from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

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
            if isinstance(exc.detail, dict):
                # 如果是字段验证错误
                error_fields = []
                for field, errors in exc.detail.items():
                    error_fields.append(f"{field}: {' '.join(errors)}")
                error_message = '；'.join(error_fields)
            else:
                # 其他类型的错误
                error_message = str(exc.detail)
        
        # 返回统一的响应格式
        response.data = {
            'code': response.status_code,
            'message': error_message,
            'data': None
        }
    
    return response 