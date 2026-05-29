from decimal import Decimal

from django.db import models


class Employee(models.Model):
    employee_id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    designation = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        ordering = ["employee_id"]

    def __str__(self) -> str:
        return f"{self.employee_id} - {self.name}"


class SalaryRecord(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="salaries",
        to_field="employee_id",
    )
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    hra = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-year", "-month", "employee_id"]
        unique_together = [["employee", "month", "year"]]

    @staticmethod
    def calculate_net(
        base: Decimal,
        hra: Decimal,
        allowances: Decimal,
        deductions: Decimal,
    ) -> Decimal:
        return base + hra + allowances - deductions

    def save(self, *args, **kwargs):
        self.net_salary = self.calculate_net(
            self.base_salary, self.hra, self.allowances, self.deductions
        )
        super().save(*args, **kwargs)
