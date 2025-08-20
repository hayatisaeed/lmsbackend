from celery import shared_task
from django.utils import timezone

from .models import Attempt
from .serializers import AttemptSubmitSerializer


@shared_task
def autosubmit_expired_attempts() -> str:
    now = timezone.now()
    attempts = Attempt.objects.filter(
        status=Attempt.Status.IN_PROGRESS, expires_at__lte=now
    )
    for attempt in attempts:
        serializer = AttemptSubmitSerializer(
            data={}, context={"attempt": attempt}
        )
        serializer.is_valid()
        serializer.save()
    return "ok"
