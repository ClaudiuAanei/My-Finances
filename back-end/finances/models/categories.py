from django.db import models

class Category(models.Model):

    TYPE_CHOICES = [
        ("income", "Income"),
        ("expense", "Expense"),
    ]
    
    name = models.CharField(max_length=255, db_index=True)
    type = models.CharField(max_length=7, choices=TYPE_CHOICES)
    users = models.ManyToManyField("auth.User", related_name="categories", blank=True)

    class Meta:
        unique_together = ("name", "type")  # Ensure unique category names per type
        indexes = [
            models.Index(fields=["name"]),  # Index for faster lookups by name
        ]

        verbose_name_plural = "Categories"
        verbose_name = "Category"

    def __str__(self):
        return self.name

    @classmethod
    def get_or_create_for_user(cls, user, name, type):
        normalized_name = name.strip().lower()
        category, _ = cls.objects.get_or_create(name=normalized_name, type=type)
        category.users.add(user)
        return category
    

class CategoryLimit(models.Model):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="category_limits")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="limits")
    monthly_budget = models.ForeignKey("MonthlyBudget", on_delete=models.CASCADE, related_name="category_limits")
    limit_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "category", "monthly_budget")  # Ensure one limit per category per monthly budget
        indexes = [
            models.Index(fields=["user"]),  # Index for faster lookups by user
            models.Index(fields=["category"]),  # Index for faster lookups by category
            models.Index(fields=["monthly_budget"]),  # Index for faster lookups by monthly budget
        ]

        verbose_name_plural = "Category Limits"
        verbose_name = "Category Limit"

    def __str__(self):
        return f"{self.category.name} limit for {self.monthly_budget.date.strftime('%B %Y')}: {self.limit_amount}"