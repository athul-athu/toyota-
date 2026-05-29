from django.contrib import admin

from payroll.models import Employee, SalaryRecord

admin.site.register(Employee)
admin.site.register(SalaryRecord)
