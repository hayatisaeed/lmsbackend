from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="courses-health"),
    path("readiness/", views.readiness, name="courses-readiness"),
    path("exams/", views.ExamListCreateView.as_view(), name="exam-list"),
    path("exams/<uuid:pk>/", views.ExamDetailView.as_view(), name="exam-detail"),
    path(
        "exams/<uuid:exam_id>/publish/",
        views.ExamPublishView.as_view(),
        name="exam-publish",
    ),
    path(
        "exams/<uuid:exam_id>/questions/",
        views.QuestionCreateView.as_view(),
        name="question-create",
    ),
    path(
        "questions/<uuid:pk>/",
        views.QuestionDetailView.as_view(),
        name="question-detail",
    ),
    path(
        "questions/<uuid:question_id>/options/",
        views.MCQOptionCreateView.as_view(),
        name="mcqoption-create",
    ),
    path(
        "questions/<uuid:question_id>/files/",
        views.QuestionFileUploadView.as_view(),
        name="question-file-upload",
    ),
    path(
        "question-files/<uuid:pk>/",
        views.QuestionFileDeleteView.as_view(),
        name="question-file-delete",
    ),
    path(
        "files/upload/question-asset/",
        views.QuestionAssetUploadView.as_view(),
        name="question-asset-upload",
    ),
    path(
        "files/upload/answer/",
        views.AnswerFileUploadView.as_view(),
        name="answer-file-upload",
    ),
    path("files/<uuid:pk>/", views.FileServeView.as_view(), name="file-serve"),
    path(
        "exams/<uuid:exam_id>/assign-to-course/",
        views.ExamAssignView.as_view(),
        name="exam-assign",
    ),
    path(
        "exams/<uuid:exam_id>/assignments/",
        views.ExamAssignmentListView.as_view(),
        name="exam-assignments",
    ),
    path(
        "exams/<uuid:exam_id>/graders/assign/",
        views.GraderAssignmentView.as_view(),
        name="exam-grader-assign",
    ),
    path(
        "exams/<uuid:exam_id>/grading-queue/",
        views.GradingQueueView.as_view(),
        name="grading-queue",
    ),
    path(
        "answers/<uuid:answer_id>/grade/",
        views.GradeAnswerView.as_view(),
        name="answer-grade",
    ),
    path(
        "attempts/<uuid:attempt_id>/finalize/",
        views.FinalizeAttemptView.as_view(),
        name="attempt-finalize",
    ),
    path(
        "attempts/<uuid:attempt_id>/release/",
        views.ReleaseAttemptView.as_view(),
        name="attempt-release",
    ),
    path(
        "exams/<uuid:exam_id>/results/release-bulk/",
        views.BulkReleaseExamResultsView.as_view(),
        name="exam-results-release-bulk",
    ),
    path("my/active-exams/", views.ActiveExamsListView.as_view(), name="active-exams"),
    path(
        "<uuid:course_id>/exams/<uuid:exam_id>/attempts/start/",
        views.AttemptStartView.as_view(),
        name="attempt-start",
    ),
    path(
        "exams/attempts/<uuid:attempt_id>/",
        views.AttemptDetailView.as_view(),
        name="attempt-detail",
    ),
    path(
        "exams/attempts/<uuid:attempt_id>/answers/<uuid:question_id>/autosave/",
        views.AnswerAutosaveView.as_view(),
        name="answer-autosave",
    ),
    path(
        "exams/attempts/<uuid:attempt_id>/submit/",
        views.AttemptSubmitView.as_view(),
        name="attempt-submit",
    ),
    path(
        "exams/attempts/<uuid:attempt_id>/result/",
        views.AttemptResultView.as_view(),
        name="attempt-result",
    ),
]
