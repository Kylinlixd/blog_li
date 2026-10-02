from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """统一分页：默认 10 条、允许客户端用 pageSize 调整、上限 100。

    响应统一为 {code, message, data: {total, items}} 信封，
    与 /api/dynamics/ 的 DynamicPagination 同款；前端由
    normalizeCollectionResponse 兼容解析。
    """

    page_size = 10
    page_size_query_param = 'pageSize'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'total': self.page.paginator.count,
                'items': data
            }
        })
