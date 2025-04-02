from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
import os
import uuid
from django.conf import settings

# Create your views here.
class AvatarUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request, *args, **kwargs):
        if 'file' not in request.FILES:
            return Response({
                'code': 400,
                'message': '未提供文件'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        file = request.FILES['file']
        
        # 验证文件大小（2MB）
        if file.size > 2 * 1024 * 1024:
            return Response({
                'code': 400,
                'message': '文件大小不能超过2MB'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 检查是否是图片文件
        allowed_types = ['image/jpeg', 'image/png', 'image/jpg']
        if file.content_type not in allowed_types:
            return Response({
                'code': 400,
                'message': '只允许上传JPG或PNG格式的图片'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 创建目录（如果不存在）
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'avatars')
        os.makedirs(upload_dir, exist_ok=True)
        
        # 生成唯一文件名
        filename = f"{uuid.uuid4().hex}{os.path.splitext(file.name)[1]}"
        file_path = os.path.join(upload_dir, filename)
        
        # 保存文件
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        # 获取URL
        file_url = f"{settings.MEDIA_URL}avatars/{filename}"
        
        # 更新用户头像
        request.user.avatar = file_url
        request.user.save()
        
        return Response({
            'code': 200,
            'data': {
                'url': file_url
            },
            'message': '头像上传成功'
        })
