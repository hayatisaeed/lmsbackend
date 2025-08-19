from django.http import JsonResponse


def healthz(_request):
    return JsonResponse({"status": "ok"})


def readyz(_request):
    # Stub readiness check
    return JsonResponse({"status": "ok"})
