from finances.models.transactions import Transaction
from finances.models.budget import MonthlyBudget
from django.db.models import Sum
from datetime import datetime
from decimal import Decimal

TYPE = "actual"  # Default transaction type


class TransactionCollection:
    def __init__(self, queryset):
        self.queryset = queryset
    
    def _calculate_total(self, queryset=None) -> Decimal:
        """
        Calculate the total amount for the transactions in the collection, 
        optionally filtered by category type.
        """

        if queryset is None:
            queryset = self.queryset
        return queryset.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    
    def get_total(self, category_type: str = "expense") -> Decimal:
        """
        Calculate the total amount for the transactions in the collection, 
        optionally filtered by category type.
        """

        if category_type in ["income", "expense"]:
            queryset = self.queryset.filter(category__type=category_type)
        else:
            queryset = self.queryset

        return self._calculate_total(queryset)
    

    def get_balance(self) -> Decimal:
        """
        Calculate the balance by subtracting total expenses from total income.
        """
        total_income = self.get_total(category_type="income")
        total_expenses = self.get_total(category_type="expense")

        return total_income - total_expenses
    

    def __getattr__(self, attr):
        return getattr(self.queryset, attr)

    def __iter__(self):
        return iter(self.queryset)
    
    def __len__(self):
        return len(self.queryset)
    

class TransactionsSelector:
    def __init__(self, user):
        self.user = user
        self._monthly_budget_cache = {}

    
    def _parse_date(self, value: datetime | str | None) -> datetime | None:
        """Utility method to parse a date from various formats."""

        # If the value is already a datetime object, return it as is
        if value is None:
            return None
        if isinstance(value, datetime):
            return value

        # Try parsing the string with common date formats
        for fmt in ("%Y-%m-%d", "%Y-%m"):
            try:
                parsed = datetime.strptime(value, fmt)
                if fmt == "%Y-%m":
                    return parsed.replace(day=1)
                return parsed
            except ValueError:
                continue
        
        # If parsing fails, return None or raise an error as needed
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None


    def get_monthly_budget(self, date: datetime):
        """Fetch the monthly budget for the user based on the provided date."""
        month_start = date.replace(day=1).date()

        if month_start not in self._monthly_budget_cache:
            self._monthly_budget_cache[month_start] = MonthlyBudget.objects.filter(
                user=self.user,
                date=month_start,
            ).first()

        return self._monthly_budget_cache[month_start]
        

    def get_transactions(self,
        selected_date: datetime | str | None = None,
        start_date: datetime | str | None = None,
        end_date: datetime | str | None = None,
        type: str = TYPE,
        category_type: str | None = None,
        categories: list[str] | None = None,
        name: str | None = None,
        apply_selected_budget_scope: bool = True) -> TransactionCollection:

        """
        Fetch transactions for the user with optional filtering by date range, type, category, and name.
        If no date range is provided, transactions will be filtered by the monthly budget of the selected date (if apply_selected_budget_scope is True).
        """

        # Start with all transactions for the user
        transactions = Transaction.objects.filter(user=self.user)

        # Build dynamic filters based on provided parameters
        normalized_type = type if type in dict(Transaction.TYPE_CHOICES) else TYPE

        filters = {
            "type": normalized_type,
            "category__type": category_type if category_type else None,
            "category__name__in": categories if categories else None,
            "name__icontains": name if name else None,
        }

        # If start_date or end_date is provided, filter by date range. 
        # Otherwise, if apply_selected_budget_scope is True, filter by the monthly budget of the selected date.
        if start_date is not None or end_date is not None:
            start_date = self._parse_date(start_date)
            end_date = self._parse_date(end_date)

            if start_date:
                filters["date__gte"] = start_date.date()
            if end_date:
                filters["date__lte"] = end_date.date()

        elif apply_selected_budget_scope:
            scoped_date = self._parse_date(selected_date) or datetime.now().replace(day=1)
            monthly_budget = self.get_monthly_budget(scoped_date)

            # Do not leak all user transactions when no budget exists for this month.
            if monthly_budget is None:
                return TransactionCollection(transactions.none())

            filters["monthly_budget"] = monthly_budget

        # Remove any filters that have None values to avoid unintended filtering
        valid_filters = {k: v for k, v in filters.items() if v is not None}

        # Apply the valid filters to the transactions queryset and select related fields for optimization
        qs = transactions.filter(**valid_filters).select_related("category", "monthly_budget")

        return TransactionCollection(qs)
    

