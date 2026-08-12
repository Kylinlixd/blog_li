from rest_framework.permissions import BasePermission


CONTENT_EDITOR_ROLES = {'admin', 'editor', 'moderator'}


def is_content_editor(user):
    return bool(
        user
        and user.is_authenticated
        and (
            user.is_staff
            or user.is_superuser
            or user.role in CONTENT_EDITOR_ROLES
        )
    )


class IsContentEditor(BasePermission):
    message = '需要内容编辑权限'

    def has_permission(self, request, view):
        return is_content_editor(request.user)


class IsUserAdmin(BasePermission):
    message = '需要管理员权限'

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_staff or user.is_superuser or user.role == 'admin')
        )
