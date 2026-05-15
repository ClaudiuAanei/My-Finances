from datetime import datetime
from decimal import Decimal

from django.db import models
from django.db.models import Sum
from django.db.models.functions import Coalesce

from finances.models.categories import Category, CategoryLimit
from finances.selectors.transactions import TransactionsSelector


class CategoryLimitsSelector(TransactionsSelector):
    def __init__(self, user):
        super().__init__(user)


    def _get_latest_category_limits_subquery(self, date: datetime):
        return CategoryLimit.objects.filter(
            user=self.user,
            category=models.OuterRef("pk"),
            monthly_budget__user=self.user,
            monthly_budget__date__lte=date,
        ).order_by("-monthly_budget__date", "-id")


    def _annotate_latest_limit_fields(self, queryset, date: datetime):
        limit_subquery = self._get_latest_category_limits_subquery(date)

        return queryset.annotate(
            limit_id=models.Subquery(limit_subquery.values("id")[:1]),
            limit_amount=models.Subquery(limit_subquery.values("limit_amount")[:1]),
            limit_date=models.Subquery(limit_subquery.values("monthly_budget__date")[:1]),
        )


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


class CategoriesSelector(CategoryLimitsSelector):
    def __init__(self, user):
        super().__init__(user)


    def _get_spent_subquery(self, date: datetime, transaction_type: str):
        return (
            self.get_transactions(selected_date=date, category_type="expense", type=transaction_type)
            .queryset.filter(category=models.OuterRef("pk"))
            .values("category")
            .annotate(total=Sum("amount"))
            .values("total")[:1]
        )

    def _get_base_categories_queryset(self):
        return Category.objects.filter(users=self.user).exclude(type="income")


    def _annotate_spent_amount(self, queryset, spent_subquery):
        return queryset.annotate(
            spent_amount=Coalesce(
                models.Subquery(spent_subquery),
                models.Value(Decimal("0.00")),
            ),
        )


    def _annotate_usage_fields(self, queryset):
        return queryset.annotate(
            remaining=models.Case(
                models.When(
                    limit_amount__isnull=False,
                    then=models.F("limit_amount") - models.F("spent_amount"),
                ),
                default=None,
            ),
            percentage_used=models.Case(
                models.When(
                    limit_amount__gt=0,
                    then=models.ExpressionWrapper(
                        models.F("spent_amount") * models.Value(Decimal("100.00")) / models.F("limit_amount"),
                        output_field=models.DecimalField(max_digits=12, decimal_places=2),
                    ),
                ),
                default=None,
            ),
        )


    def get_categories_info(self, date: datetime, type: str = "actual"):
        spent_subquery = self._get_spent_subquery(date, type)

        categories = self._get_base_categories_queryset()
        categories = self._annotate_latest_limit_fields(categories, date)
        categories = self._annotate_spent_amount(categories, spent_subquery)
        categories = self._annotate_usage_fields(categories)

        return categories.order_by("id")