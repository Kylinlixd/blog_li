# API Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close public registration, preserve article relationships on update, and remove unsafe production error disclosure while keeping public reading APIs stable.

**Architecture:** Retain the existing DRF viewsets and response envelope. Put trust-boundary validation in permissions and serializers, reuse the existing authenticated API paths, and avoid database migrations.

**Tech Stack:** Django 5.1, Django REST Framework 3.16, Simple JWT, Django TestCase/APITestCase.

---

### Task 1: Restrict account creation to administrators

**Files:**
- Modify: `apps/user/tests.py`
- Modify: `apps/user/views.py`

- [ ] **Step 1: Write failing permission tests**

```python
def test_anonymous_registration_is_denied(self):
    response = self.client.post('/api/auth/register/', {
        'username': 'visitor',
        'email': 'visitor@example.com',
        'password': 'safe-password-123',
    })
    self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

def test_admin_can_create_an_account(self):
    self.user.is_staff = True
    self.user.save(update_fields=['is_staff'])
    self.client.force_authenticate(self.user)
    response = self.client.post('/api/auth/register/', {
        'username': 'writer',
        'email': 'writer@example.com',
        'password': 'safe-password-123',
    })
    self.assertEqual(response.status_code, status.HTTP_200_OK)
```

- [ ] **Step 2: Run the tests and verify the anonymous case fails**

Run: `python manage.py test apps.user.tests.AuthTests`

Expected: FAIL because registration currently allows anonymous requests.

- [ ] **Step 3: Apply action-specific permissions**

```python
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated

def get_permissions(self):
    if self.action == 'login':
        return [AllowAny()]
    if self.action == 'register':
        return [IsAdminUser()]
    return [IsAuthenticated()]
```

- [ ] **Step 4: Run authentication tests**

Run: `python manage.py test apps.user.tests.AuthTests`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/user/tests.py apps/user/views.py
git commit -m "fix: restrict account creation to admins"
```

### Task 2: Preserve article metadata and file relationships on update

**Files:**
- Modify: `apps/dynamic/tests.py`
- Modify: `apps/dynamic/serializers.py`
- Modify: `apps/dynamic/views.py`

- [ ] **Step 1: Write a failing authenticated update test**

```python
def test_update_preserves_category_tags_and_media(self):
    self.client.force_authenticate(self.user)
    second_category = Category.objects.create(name='后端实践')
    second_tag = Tag.objects.create(name='Django')
    response = self.client.put(f'/api/dynamics/{self.published.pk}/', {
        'title': '更新后的标题',
        'content': '更新后的正文',
        'type': 'image',
        'status': 'published',
        'categoryId': second_category.pk,
        'tags': [second_tag.pk],
        'mediaUrls': ['/media/cover.png'],
        'fileIds': [],
    }, format='json')
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.published.refresh_from_db()
    self.assertEqual(self.published.category, second_category)
    self.assertEqual(list(self.published.tags.values_list('id', flat=True)), [second_tag.pk])
    self.assertEqual(self.published.media_urls, ['/media/cover.png'])
```

- [ ] **Step 2: Run the test and verify current update behavior**

Run: `python manage.py test apps.dynamic.tests.DynamicAPITests.test_update_preserves_category_tags_and_media`

Expected: FAIL if the create serializer does not correctly update write-only relationships.

- [ ] **Step 3: Add one explicit update implementation to `DynamicCreateSerializer`**

```python
def update(self, instance, validated_data):
    media_urls = validated_data.pop('mediaUrls', None)
    file_ids = validated_data.pop('fileIds', None)
    category_id = validated_data.pop('categoryId', None)
    tag_ids = validated_data.pop('tags', None)
    validated_data.pop('createdAt', None)

    for field, value in validated_data.items():
        setattr(instance, field, value)
    if media_urls is not None:
        instance.media_urls = media_urls
    if category_id is not None:
        instance.category_id = category_id
    instance.save()
    if file_ids is not None:
        instance.files.set(file_ids)
    if tag_ids is not None:
        instance.tags.set(tag_ids)
    return instance
```

- [ ] **Step 4: Run dynamic tests**

Run: `python manage.py test apps.dynamic.tests.DynamicAPITests`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/dynamic/tests.py apps/dynamic/serializers.py apps/dynamic/views.py
git commit -m "fix: preserve article relationships on update"
```

### Task 3: Stop exposing raw backend exceptions

**Files:**
- Modify: `apps/dynamic/views.py`
- Modify: `apps/upload/views.py`
- Modify: `apps/user/views.py`
- Modify: relevant app tests

- [ ] **Step 1: Add a response-disclosure regression test**

```python
@patch('apps.dynamic.views.Dynamic.objects.filter', side_effect=RuntimeError('database secret'))
def test_search_does_not_expose_internal_exception(self, _filter):
    response = self.client.get('/api/blog/search/', {'keyword': 'Vue'})
    self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    self.assertNotIn('database secret', str(response.data))
```

- [ ] **Step 2: Run the regression test and verify it fails on a raw `str(e)` path**

Run the exact test module containing the regression.

Expected: FAIL because one or more 500 responses include raw exception text.

- [ ] **Step 3: Replace raw exception disclosure with logging and stable messages**

```python
logger.exception('Search request failed')
return Response(
    {'code': 500, 'message': '服务暂时不可用，请稍后重试'},
    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
)
```

Apply this only to genuine server-error branches. Preserve specific 400/404 validation messages and DRF serializer errors.

- [ ] **Step 4: Run all backend tests**

Run: `python manage.py check && python manage.py test`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps blog
git commit -m "refactor: harden API error responses"
```

### Task 4: Verify production configuration and record the backend node

**Files:**
- Create: `docs/DELIVERY_2026-07-27.md`

- [ ] **Step 1: Run the backend gate**

Run: `python manage.py check && python manage.py test`

Expected: PASS.

- [ ] **Step 2: Run production checks with ephemeral safe values**

Run with `DJANGO_DEBUG=False`, a temporary 50+ character secret, `DJANGO_ALLOWED_HOSTS=leexd.top`, trusted HTTPS origin, and SQLite enabled: `python manage.py check --deploy`.

Expected: no errors; any warning intentionally owned by Nginx is recorded.

- [ ] **Step 3: Record evidence and commit**

```bash
git add docs/DELIVERY_2026-07-27.md
git commit -m "docs: record backend hardening delivery"
```

