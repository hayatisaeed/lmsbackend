from rest_framework.throttling import SimpleRateThrottle


class AutosaveThrottle(SimpleRateThrottle):
    scope = "courses_autosave"


class AnswerFileDeleteThrottle(SimpleRateThrottle):
    scope = "courses_answer_file_delete"
