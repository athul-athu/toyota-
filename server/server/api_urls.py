from django.urls import path

from payroll import views as payroll_views
from server.views import auth

urlpatterns = [
    path("auth/signup/", auth.signup, name="api-auth-signup"),
    path("auth/login/", auth.login, name="api-auth-login"),
    path("auth/me/", auth.me, name="api-auth-me"),
    path("auth/logout/", auth.logout, name="api-auth-logout"),
    path("payroll/preview/", payroll_views.preview_upload, name="payroll-preview"),
    path("payroll/import/", payroll_views.import_payroll, name="payroll-import"),
    path("payroll/employees/", payroll_views.list_employees, name="payroll-employees"),
    path("payroll/salaries/", payroll_views.list_salaries, name="payroll-salaries"),
    path("payroll/generate-pdfs/", payroll_views.generate_pdfs, name="payroll-pdfs"),
    path("payroll/slips/", payroll_views.list_stored_slips, name="payroll-slips"),
    path(
        "payroll/process-and-send/",
        payroll_views.process_and_send,
        name="payroll-process-send",
    ),
    path(
        "payroll/process-period/",
        payroll_views.process_period_api,
        name="payroll-process-period",
    ),
]
