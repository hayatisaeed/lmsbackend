from django.http import HttpResponse, JsonResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest


def healthz(_request):
    return JsonResponse({"status": "ok"})


def readyz(_request):
    # Stub readiness check
    return JsonResponse({"status": "ok"})


def metrics(_request):
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)
