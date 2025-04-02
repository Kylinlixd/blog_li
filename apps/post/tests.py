from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.post.models import Post
from apps.category.models import Category
from apps.tag.models import Tag
from apps.user.models import User
from django.utils import timezone
import datetime

class PostAPITests(TransactionTestCase):
    def setUp(self):
        self.client = APIClient()
        
        # 创建测试用户
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # 创建测试分类
        self.category = Category.objects.create(
            name='测试分类',
            description='这是一个测试分类'
        )
        
        # 创建测试标签
        self.tag = Tag.objects.create(name='测试标签')
        
        # 创建测试文章
        self.post = Post.objects.create(
            title='测试文章',
            content='这是测试文章的内容',
            summary='这是测试文章的摘要',
            category=self.category,
            author=self.user,
            status='published'
        )
        self.post.tags.add(self.tag)
        
        # 创建更多测试文章
        for i in range(15):
            Post.objects.create(
                title=f'测试文章 {i+1}',
                content=f'这是测试文章 {i+1} 的内容',
                summary=f'这是测试文章 {i+1} 的摘要',
                category=self.category,
                author=self.user,
                status='published',
                create_time=timezone.now() - datetime.timedelta(days=i)
            )
    
    def tearDown(self):
        # 清理测试数据
        Post.objects.all().delete()
        Category.objects.all().delete()
        Tag.objects.all().delete()
        User.objects.all().delete()
    
    def test_get_post_list(self):
        """测试获取文章列表"""
        url = '/blog/posts/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['message'], 'success')
        self.assertIn('data', response.data)
        self.assertIn('total', response.data['data'])
        self.assertIn('items', response.data['data'])
    
    def test_get_post_detail(self):
        """测试获取文章详情"""
        url = f'/blog/posts/{self.post.pk}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['message'], 'success')
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['title'], '测试文章')
    
    def test_get_adjacent_posts(self):
        """测试获取相邻文章"""
        url = f'/blog/posts/{self.post.pk}/adjacent/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['message'], 'success')
        self.assertIn('data', response.data)
        self.assertIn('prev', response.data['data'])
        self.assertIn('next', response.data['data'])
    
    def test_increment_view_count(self):
        """测试增加文章浏览量"""
        url = f'/blog/posts/{self.post.pk}/view/'
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['message'], 'success')
        
        # 验证浏览量是否增加
        self.post.refresh_from_db()
        self.assertEqual(self.post.views, 1)
    
    def test_get_recent_posts(self):
        """测试获取最新文章"""
        url = '/blog/posts/recent'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['message'], 'success')
        self.assertIn('data', response.data)
        self.assertEqual(len(response.data['data']), 5)  # 默认返回5条
    
    def test_get_hot_posts(self):
        """测试获取热门文章"""
        # 设置一些文章的浏览量
        Post.objects.filter(pk=self.post.pk).update(views=100)
        
        url = '/blog/posts/hot'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['message'], 'success')
        self.assertIn('data', response.data)
        self.assertEqual(len(response.data['data']), 5)  # 默认返回5条
    
    def test_get_category_posts(self):
        """测试获取分类下的文章"""
        url = f'/blog/categories/{self.category.pk}/posts'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['message'], 'success')
        self.assertIn('data', response.data)
        self.assertIn('total', response.data['data'])
        self.assertIn('items', response.data['data'])
    
    def test_get_tag_posts(self):
        """测试获取标签下的文章"""
        url = f'/blog/tags/{self.tag.pk}/posts'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['message'], 'success')
        self.assertIn('data', response.data)
        self.assertIn('total', response.data['data'])
        self.assertIn('items', response.data['data'])
    
    def test_search_posts(self):
        """测试搜索文章"""
        url = '/blog/posts/'
        response = self.client.get(url, {'keyword': '测试文章'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['message'], 'success')
        self.assertIn('data', response.data)
        self.assertIn('total', response.data['data'])
        self.assertIn('items', response.data['data'])
        self.assertTrue(len(response.data['data']['items']) > 0)
