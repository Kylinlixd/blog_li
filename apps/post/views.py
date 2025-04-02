from models import Post 
from rest_framework.permissions import IsAuthenticated
# Create your views here.
from rest_framework.viewsets import ModelViewSet
from serializers import PostSerializer


class PostViewSet(ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        
        # 过滤条件
        if 'categoryId' in params:
            queryset = queryset.filter(category_id=params['categoryId'])
        if 'tagId' in params:
            queryset = queryset.filter(tags__id=params['tagId'])
        if 'status' in params:
            queryset = queryset.filter(status=params['status'])
        if 'keyword' in params:
            queryset = queryset.filter(Q(title__icontains=params['keyword']) | 
                                      Q(content__icontains=params['keyword']))
        return queryset