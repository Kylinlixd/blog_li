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
        
        # 处理401未授权错误
        if response.status_code == 401:
            error_message = '请先登录'
            
            # 判断是否是JWT令牌格式错误
            if hasattr(exc, 'detail') and isinstance(exc.detail, dict):
                if 'code' in exc.detail and exc.detail.get('code') == 'bad_authorization_header':
                    error_message = '认证格式错误，请确保使用"Bearer access_token"格式'
                elif 'code' in exc.detail and exc.detail.get('code') == 'token_not_valid':
                    error_message = '令牌无效或已过期，请使用有效的访问令牌(access_token)'
        
        # 处理验证错误
        elif hasattr(exc, 'detail'):
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
        
        request = context.get('request')
        # 返回统一的响应格式
        response_data = {
            'code': response.status_code,
            'message': error_message,
            'data': None,
            'requestId': getattr(request, 'request_id', None),
        }
            
        response.data = response_data
    
    return response
