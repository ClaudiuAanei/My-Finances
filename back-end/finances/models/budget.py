from django.db import models

class MonthlyBudget(models.Model):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="monthly_budgets")
    saving_goal = models.DecimalField(max_digits=10, decimal_places=2, default=0) # type: ignore
    date = models.DateField(db_index=True)

    class Meta:
        unique_together = ("user", "date")

    def __str__(self):
        return f"{self.date.strftime('%B %Y')}"
    

class YearlyBudget(models.Model):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="yearly_budgets")
    saving_goal = models.DecimalField(max_digits=10, decimal_places=2, default=0) # type: ignore
    year = models.IntegerField()

    def __str__(self):
        return f"{self.year}"