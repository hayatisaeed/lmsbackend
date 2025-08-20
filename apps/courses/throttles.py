from rest_framework.throttling import SimpleRateThrottle


class AutosaveThrottle(SimpleRateThrottle):
    scope = "courses_autosave"
