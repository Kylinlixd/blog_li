from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.user.permissions import IsContentEditor


class SystemHealthView(APIView):
    """Minimal authenticated liveness check for the admin shell."""

    permission_classes = [IsAuthenticated, IsContentEditor]

    def get(self, request):
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'status': 'ok',
                'checked_at': timezone.now().isoformat(),
            },
        })
