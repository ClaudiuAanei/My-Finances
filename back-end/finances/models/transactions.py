from django.db import models
from django.contrib.auth.models import User
from finances.models.categories import Category
from .budget import MonthlyBudget


class Transaction(models.Model):
    TYPE_CHOICES = [
        ("actual", "Actual"),
        ("planned", "Planned"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")
    date = models.DateField()
    type = models.CharField(max_length=7, choices=TYPE_CHOICES, default="actual")
    name = models.CharField(max_length=255, default="No name")
    description = models.CharField(max_length=255, default="No description")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="EUR")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="transactions")
    monthly_budget = models.ForeignKey(MonthlyBudget, on_delete=models.CASCADE, related_name="transactions")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "date", "name", "amount", "category", "monthly_budget")
        indexes = [
            models.Index(fields=["user", "date", "name", "amount", "category", "monthly_budget"]),
        ]
        verbose_name_plural = "Transactions"
        verbose_name = "Transaction"

    def __str__(self):
        return f"{self.name}: {self.amount} on {self.date}"
    
    
    
