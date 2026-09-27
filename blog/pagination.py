from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """统一分页：默认 10 条、允许客户端用 pageSize 调整、上限 100。

    全局默认的 PageNumberPagination 不开放每页条数，
    管理端把列表切到 20/50/100 时后端仍然只返回 10 条，页码与总数会对不上。
    """

    page_size = 10
    page_size_query_param = 'pageSize'
    max_page_size = 100
