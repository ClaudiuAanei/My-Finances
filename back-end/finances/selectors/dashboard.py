from datetime import datetime
from decimal import Decimal

from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce

from finances.selectors.transactions import TransactionsSelector
from finances.selectors.categories import CategoriesSelector
from finances.models.transactions import Transaction
from finances.models.budget import MonthlyBudget


class DashboardCollection:
    def __init__(self, queryset):
        self.queryset = queryset

    def get_available_years(self):
        return [value.year for value in self.queryset.dates("date", "year")]
    
    def get_available_months(self):
        return [value.month for value in self.queryset.dates("date", "month")]

    
class DashboardSelector(TransactionsSelector):

    def __init__(self, user, selected_date: datetime):
        super().__init__(user)
        self.selected_date = selected_date.replace(day=1)  # Normalize to the first day of the month for consistency
        self._type = "actual"  # Default to actual transactions, can be overridden by method parameters


    def _set_type(self, transaction_type: str):
        if transaction_type in dict(Transaction.TYPE_CHOICES):
            self._type = transaction_type
        else:
            raise ValueError(f"Invalid transaction type: {transaction_type}")
        
    
    def get_user_budgets(self):
        return MonthlyBudget.objects.filter(user=self.user)


    def get_summary(self):
        transactions_queryset = self.get_transactions(type=self._type, selected_date=self.selected_date).queryset

        totals = transactions_queryset.aggregate(
            income=Coalesce(
                Sum("amount", filter=Q(category__type="income")),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            expense=Coalesce(
                Sum("amount", filter=Q(category__type="expense")),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
        )

        income: Decimal = totals["income"]
        expenses: Decimal = totals["expense"]
        balance: Decimal = income - expenses

        return {
            "income": income,
            "expense": expenses,
            "balance": balance
        }


    def get_monthly_status(self, summary: dict, monthly_budget=None):
        monthly_budget = monthly_budget or self.get_monthly_budget(self.selected_date)
        if not monthly_budget:
            return None

        saving_target = monthly_budget.saving_goal or 0
        remaining_to_target = saving_target - summary["balance"]
        progress_percentage = (summary["balance"] / saving_target * 100) if saving_target else None

        return {
            "saving_target": saving_target,
            "current_saved": summary["balance"],
            "remaining_to_target": remaining_to_target,
            "progress_percentage": progress_percentage
        }
    

    def get_categories_info(self):
        categories_selector = CategoriesSelector(self.user)
        return categories_selector.get_categories_info(self.selected_date, type=self._type)


    def get_dashboard_data(self, transaction_type: str = "actual"): # Default to "actual" transactions
        self._set_type(transaction_type)

        monthly_budget = self.get_monthly_budget(self.selected_date)
        summary = self.get_summary()

        collection = DashboardCollection(self.get_user_budgets())
        
        return {
            "type": transaction_type,
            "info": f"Budget : {str(monthly_budget)}" if monthly_budget else "No budget set",
            "available_years": collection.get_available_years(),
            "available_months": collection.get_available_months(),
            "summary": summary,
            "monthly_status": self.get_monthly_status(summary, monthly_budget=monthly_budget),
            "categories": self.get_categories_info()
        }
    