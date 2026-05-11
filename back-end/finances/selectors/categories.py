from finances.models.categories import Category, CategoryLimit
from django.db import models
from datetime import datetime

class CategoriesSelector:
    def __init__(self, user):
        self.user = user


    def _get_category_limits(self, date: datetime):
        category_limits = CategoryLimit.objects.filter(
            user=self.user,
            category=models.OuterRef("pk"),
            monthly_budget__user=self.user,
            monthly_budget__date__year__lte=date.year,
            monthly_budget__date__month__lte=date.month,
        ).values("limit_amount").order_by("-monthly_budget__date")[:1]

        return category_limits


    def get_categories(self, date: datetime):
        limit_subquery = self._get_category_limits(date)

        categories = Category.objects.filter(users=self.user).annotate(
            limit_id=models.Subquery(limit_subquery.values("id")[:1]),
            limit_amount=models.Subquery(limit_subquery.values("limit_amount")[:1]),
            limit_date=models.Subquery(limit_subquery.values("monthly_budget__date")[:1]),
        ).exclude(type="income").order_by("id")

        return categories
    

class CategoryLimitsSelector:
    def __init__(self, user):
        self.user = user
    

    def _filter_category_limits_by_id(self, category_limits, limit_id: int | None):
        if limit_id is not None:
            category_limits = category_limits.filter(id=limit_id)
        return category_limits


    def get_category_limits(self, category_id: int, limit_id: int | None = None):
        category_limits = CategoryLimit.objects.filter(
            user=self.user,
            category=category_id,
            monthly_budget__user=self.user,
        ).select_related("category", "monthly_budget").order_by("-monthly_budget__date")

        category_limits = self._filter_category_limits_by_id(category_limits, limit_id)

        return category_limits