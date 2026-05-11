from datetime import datetime, timedelta

from finances.models.transactions import Transaction
from finances.models.budget import MonthlyBudget
from finances.models.categories import Category, CategoryLimit

from django.db.models import Sum, Q

class MonthlyBudgetSelector:
    def __init__(self, user, date: datetime):
        self.user = user
        self.date = date.replace(day=1)  # Normalize to the first day of the month for consistency

    def _get_meta_info(self):
        """Get meta information about available years, months and the selected date in a human-readable format."""
        selected_date = self.date.strftime("%B %Y")

        available_years = MonthlyBudget.objects.filter(user=self.user).dates("date", "year").values_list("date__year", flat=True).distinct()
        available_months = MonthlyBudget.objects.filter(user=self.user, date__year=self.date.year).dates("date", "month").values_list("date__month", flat=True).distinct()

        return {
            "selected_date": selected_date,
            "available_years": list(available_years),
            "available_months": list(available_months)
        }

    def _get_monthly_budget(self):
        """Get the monthly budget for the selected month."""

        return MonthlyBudget.objects.filter(user=self.user, date__month=self.date.month, date__year=self.date.year).first()
    

    def _get_total(self, date: datetime, transaction_type: str = "actual", category_id: int | None = None, category_type: str | None = None) -> float:
        """Get the total amount for the specified filters."""
        filters = {
            "user": self.user,
            "date__month": date.month,
            "date__year": date.year,
            "type": transaction_type
        }
        if category_type:
            filters["category__type"] = category_type
        
        if category_id:
            filters["category_id"] = category_id

        total = Transaction.objects.filter(**filters).aggregate(total=Sum("amount"))["total"] or 0

        return total
    
    def _get_starting_balance(self, date: datetime, transaction_type: str = "actual") -> float:
        """Get the starting balance from previous months."""
        previous_month = date.replace(day=1) - timedelta(days=1)
        filters = {
            "user": self.user,
            "date__lte": previous_month,
            "type": transaction_type
        }
        total_income = Transaction.objects.filter(**filters, category__type="income").aggregate(total=Sum("amount"))["total"] or 0
        total_expenses = Transaction.objects.filter(**filters, category__type="expense").aggregate(total=Sum("amount"))["total"] or 0

        return total_income - total_expenses
    

    def _get_latest_limits(self):
        """Get the latest limits for each category up to the selected month."""
        # For each category, prefer the selected month limit; if missing,
        # fall back to the closest previous month with a defined limit.
        limits_qs = (
            CategoryLimit.objects.filter(
                monthly_budget__user=self.user,
                monthly_budget__date__lte=self.date,
            )
            .select_related("category", "monthly_budget")
            .order_by("category_id", "-monthly_budget__date", "-id")
        )

        latest_limits = {}
        for limit in limits_qs:
            latest_limits.setdefault(limit.category_id, limit)
        
        return latest_limits
    
    def _get_categories_info(self, transaction_type="actual"):
        categories = Category.objects.filter(users=self.user).exclude(type="income").distinct()
        
        latest_limits = self._get_latest_limits()
        categories_info = []

        for category in categories:
            total = self._get_total(self.date, transaction_type=transaction_type, category_id=category.id, category_type=category.type)
            limit = latest_limits.get(category.id)
            limit_amount = limit.limit_amount if limit else None
            categories_info.append({
                "id": category.id,
                "name": category.name,
                "type": category.type,
                "spent": total,
                "limit_id": limit.id if limit else None,
                "limit_amount": limit_amount,
                "remaining": limit_amount - total if limit_amount is not None else None,
                "percentage_used": (total / limit_amount * 100) if limit_amount else None
            })

        return categories_info

    def set_monthly_budget_target(self, target_amount):
        monthly_budget = self._get_monthly_budget()
        if monthly_budget:
            monthly_budget.saving_goal = target_amount
            monthly_budget.save()
            
        return monthly_budget


    def get_dashboard_data(self, transaction_type="actual"):
        """
        
        Main method to get all dashboard data based on the selected month and transaction type.
        It gathers the monthly budget, meta info about available dates, calculates total income and expenses,
        and compiles category info with limits and spending.

        """
        # Get or create monthly budget for the given date
        monthly_budget = self._get_monthly_budget()

        # Get meta info about available dates and selected date
        meta = self._get_meta_info()

        # Calculate total income and expenses for the month
        income = self._get_total(self.date, transaction_type=transaction_type, category_type="income")
        expense = self._get_total(self.date, transaction_type=transaction_type, category_type="expense")

        # Calculate starting balance from previous months
        previous_month_balance = self._get_starting_balance(self.date, transaction_type=transaction_type)

        # Calculate current balance by adding income and subtracting expenses from the starting balance
        balance = previous_month_balance + income - expense

        # Calculate progress towards saving goal if a monthly budget exists
        monthly_target = {
            "saving_target": monthly_budget.saving_goal if monthly_budget else None,
            "current_saved": balance,
            "remaining_to_target": balance - monthly_budget.saving_goal if monthly_budget else None,
            "progress_percentage": (balance / monthly_budget.saving_goal * 100) if monthly_budget and monthly_budget.saving_goal > 0 else None,
        }
        
        # Get categories info with limits and spending
        categories_info = self._get_categories_info(transaction_type=transaction_type)

        return {
            "type": transaction_type,
            "budget_id": monthly_budget.id if monthly_budget else None,
            "budget": str(monthly_budget) if monthly_budget else "No budget set",
            "summary": {
                "income": income,
                "expense": expense,
                "balance": balance,
            },

            "monthly_target": monthly_target if monthly_budget else None,
            "categories": categories_info if monthly_budget else [],
            **meta
        }



        






    
