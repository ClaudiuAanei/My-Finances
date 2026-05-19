from datetime import datetime, date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from finances.models.budget import MonthlyBudget
from finances.models.categories import Category, CategoryLimit
from finances.models.transactions import Transaction
from finances.selectors.categories import CategoriesSelector
from finances.selectors.dashboard import DashboardSelector
from finances.selectors.transactions import TransactionsSelector


class TransactionsSelectorParseDate(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.selector = TransactionsSelector(self.user)

    def test_parse_date_from_datetime(self):
        dt = datetime(2024, 3, 15)
        self.assertEqual(self.selector._parse_date(dt), dt)

    def test_parse_date_from_ymd_string(self):
        result = self.selector._parse_date("2024-03-15")
        self.assertEqual(result, datetime(2024, 3, 15))

    def test_parse_date_from_ym_string_normalizes_to_first_day(self):
        result = self.selector._parse_date("2024-03")
        self.assertEqual(result, datetime(2024, 3, 1))

    def test_parse_date_none_returns_none(self):
        self.assertIsNone(self.selector._parse_date(None))

    def test_parse_date_invalid_string_returns_none(self):
        self.assertIsNone(self.selector._parse_date("not-a-date"))


class TransactionsSelectorGetTransactions(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.other_user = User.objects.create_user(username="otheruser", password="password")

        self.expense_category = Category.objects.create(name="food", type="expense")
        self.expense_category.users.add(self.user)

        self.income_category = Category.objects.create(name="salary", type="income")
        self.income_category.users.add(self.user)

        self.budget = MonthlyBudget.objects.create(
            user=self.user, date=date(2024, 3, 1), saving_goal=Decimal("500.00")
        )

        self.t1 = Transaction.objects.create(
            user=self.user, date=date(2024, 3, 10), type="actual",
            name="Groceries", amount=Decimal("50.00"),
            category=self.expense_category, monthly_budget=self.budget,
        )
        self.t2 = Transaction.objects.create(
            user=self.user, date=date(2024, 3, 20), type="planned",
            name="Planned groceries", amount=Decimal("60.00"),
            category=self.expense_category, monthly_budget=self.budget,
        )
        self.t3 = Transaction.objects.create(
            user=self.user, date=date(2024, 3, 5), type="actual",
            name="March salary", amount=Decimal("2000.00"),
            category=self.income_category, monthly_budget=self.budget,
        )

        self.selector = TransactionsSelector(self.user)

    def test_get_transactions_returns_only_actual_by_default(self):
        result = self.selector.get_transactions(selected_date=datetime(2024, 3, 1))
        names = [t.name for t in result]
        self.assertIn("Groceries", names)
        self.assertIn("March salary", names)
        self.assertNotIn("Planned groceries", names)

    def test_get_transactions_returns_planned_when_specified(self):
        result = self.selector.get_transactions(selected_date=datetime(2024, 3, 1), type="planned")
        names = [t.name for t in result]
        self.assertIn("Planned groceries", names)
        self.assertNotIn("Groceries", names)

    def test_get_transactions_no_budget_returns_empty(self):
        result = self.selector.get_transactions(selected_date=datetime(2025, 6, 1))
        self.assertEqual(len(result), 0)

    def test_get_transactions_filters_by_date_range(self):
        result = self.selector.get_transactions(
            start_date="2024-03-15", end_date="2024-03-31",
            type="planned",
            apply_selected_budget_scope=False,
        )
        names = [t.name for t in result]
        self.assertIn("Planned groceries", names)
        self.assertNotIn("Groceries", names)

    def test_get_transactions_filters_by_name(self):
        result = self.selector.get_transactions(
            selected_date=datetime(2024, 3, 1), name="grocer"
        )
        names = [t.name for t in result]
        self.assertIn("Groceries", names)
        self.assertNotIn("March salary", names)


class TransactionCollectionTotals(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")

        self.expense_category = Category.objects.create(name="food", type="expense")
        self.expense_category.users.add(self.user)

        self.income_category = Category.objects.create(name="salary", type="income")
        self.income_category.users.add(self.user)

        self.budget = MonthlyBudget.objects.create(
            user=self.user, date=date(2024, 3, 1), saving_goal=Decimal("500.00")
        )

        Transaction.objects.create(
            user=self.user, date=date(2024, 3, 5), type="actual",
            name="March salary", amount=Decimal("2000.00"),
            category=self.income_category, monthly_budget=self.budget,
        )
        Transaction.objects.create(
            user=self.user, date=date(2024, 3, 10), type="actual",
            name="Groceries", amount=Decimal("300.00"),
            category=self.expense_category, monthly_budget=self.budget,
        )

        self.selector = TransactionsSelector(self.user)

    def test_get_total_expense(self):
        collection = self.selector.get_transactions(selected_date=datetime(2024, 3, 1))
        self.assertEqual(collection.get_total(category_type="expense"), Decimal("300.00"))

    def test_get_total_income(self):
        collection = self.selector.get_transactions(selected_date=datetime(2024, 3, 1))
        self.assertEqual(collection.get_total(category_type="income"), Decimal("2000.00"))

    def test_get_balance(self):
        collection = self.selector.get_transactions(selected_date=datetime(2024, 3, 1))
        self.assertEqual(collection.get_balance(), Decimal("1700.00"))


class CategoriesSelectorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")

        self.food = Category.objects.create(name="food", type="expense")
        self.food.users.add(self.user)

        self.income_cat = Category.objects.create(name="salary", type="income")
        self.income_cat.users.add(self.user)

        self.budget = MonthlyBudget.objects.create(
            user=self.user, date=date(2024, 3, 1), saving_goal=Decimal("500.00")
        )

        Transaction.objects.create(
            user=self.user, date=date(2024, 3, 10), type="actual",
            name="Groceries", amount=Decimal("150.00"),
            category=self.food, monthly_budget=self.budget,
        )

        CategoryLimit.objects.create(
            user=self.user, category=self.food,
            monthly_budget=self.budget, limit_amount=Decimal("400.00"),
        )

        self.selector = CategoriesSelector(self.user)

    def test_get_categories_info_excludes_income(self):
        result = self.selector.get_categories_info(datetime(2024, 3, 1))
        types = [c.type for c in result]
        self.assertNotIn("income", types)

    def test_get_categories_info_annotates_spent_amount(self):
        result = self.selector.get_categories_info(datetime(2024, 3, 1))
        food = next(c for c in result if c.name == "food")
        self.assertEqual(food.spent_amount, Decimal("150.00"))

    def test_get_categories_info_annotates_limit_amount(self):
        result = self.selector.get_categories_info(datetime(2024, 3, 1))
        food = next(c for c in result if c.name == "food")
        self.assertEqual(food.limit_amount, Decimal("400.00"))

    def test_get_categories_info_calculates_remaining(self):
        result = self.selector.get_categories_info(datetime(2024, 3, 1))
        food = next(c for c in result if c.name == "food")
        self.assertEqual(food.remaining, Decimal("250.00"))

    def test_get_category_limits_returns_limits_for_category(self):
        result = self.selector.get_category_limits(self.food.id)
        self.assertEqual(result.count(), 1)
        self.assertEqual(result[0].limit_amount, Decimal("400.00"))

    def test_get_category_limits_filters_by_limit_id(self):
        limit = CategoryLimit.objects.get(user=self.user, category=self.food)
        result = self.selector.get_category_limits(self.food.id, limit_id=limit.id)
        self.assertEqual(result.count(), 1)

    def test_get_category_limits_nonexistent_limit_id_returns_empty(self):
        result = self.selector.get_category_limits(self.food.id, limit_id=99999)
        self.assertEqual(result.count(), 0)


class DashboardSelectorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")

        self.expense_category = Category.objects.create(name="food", type="expense")
        self.expense_category.users.add(self.user)

        self.income_category = Category.objects.create(name="salary", type="income")
        self.income_category.users.add(self.user)

        self.budget = MonthlyBudget.objects.create(
            user=self.user, date=date(2024, 3, 1), saving_goal=Decimal("500.00")
        )

        Transaction.objects.create(
            user=self.user, date=date(2024, 3, 5), type="actual",
            name="March salary", amount=Decimal("2000.00"),
            category=self.income_category, monthly_budget=self.budget,
        )
        Transaction.objects.create(
            user=self.user, date=date(2024, 3, 10), type="actual",
            name="Groceries", amount=Decimal("300.00"),
            category=self.expense_category, monthly_budget=self.budget,
        )

        self.selector = DashboardSelector(self.user, selected_date=datetime(2024, 3, 15))

    def test_get_summary_returns_correct_income(self):
        summary = self.selector.get_summary()
        self.assertEqual(summary["income"], Decimal("2000.00"))

    def test_get_summary_returns_correct_expense(self):
        summary = self.selector.get_summary()
        self.assertEqual(summary["expense"], Decimal("300.00"))

    def test_get_summary_returns_correct_balance(self):
        summary = self.selector.get_summary()
        self.assertEqual(summary["balance"], Decimal("1700.00"))

    def test_get_monthly_status_with_saving_goal(self):
        summary = self.selector.get_summary()
        status = self.selector.get_monthly_status(summary)
        self.assertEqual(status["saving_target"], Decimal("500.00"))
        self.assertEqual(status["current_saved"], Decimal("1700.00"))
        self.assertEqual(status["remaining_to_target"], Decimal("-1200.00"))

    def test_get_monthly_status_no_budget_returns_empty_dict(self):
        selector = DashboardSelector(self.user, selected_date=datetime(2025, 6, 1))
        summary = {"income": Decimal("0"), "expense": Decimal("0"), "balance": Decimal("0")}
        result = selector.get_monthly_status(summary)
        self.assertEqual(result, {})

    def test_set_type_invalid_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.selector._set_type("invalid_type")

    def test_get_dashboard_data_contains_expected_keys(self):
        data = self.selector.get_dashboard_data()
        for key in ("summary", "monthly_status", "categories"):
            self.assertIn(key, data)
