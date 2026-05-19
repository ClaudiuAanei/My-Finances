from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from finances.models.budget import MonthlyBudget
from finances.models.categories import Category
from finances.models.transactions import Transaction


class DashboardViewTests(APITestCase):
	def setUp(self):
		self.user = User.objects.create_user(username="dashboard-user", password="password")
		self.other_user = User.objects.create_user(username="other-user", password="password")
		self.url = reverse("dashboard-list")

		self.expense_category = Category.objects.create(name="food", type="expense")
		self.expense_category.users.add(self.user)

		self.income_category = Category.objects.create(name="salary", type="income")
		self.income_category.users.add(self.user)

		self.other_user_category = Category.objects.create(name="travel", type="expense")
		self.other_user_category.users.add(self.other_user)

		self.march_budget = MonthlyBudget.objects.create(
			user=self.user,
			date=date(2024, 3, 1),
			saving_goal=Decimal("500.00"),
		)
		self.april_budget = MonthlyBudget.objects.create(
			user=self.user,
			date=date(2024, 4, 1),
			saving_goal=Decimal("900.00"),
		)
		self.other_user_budget = MonthlyBudget.objects.create(
			user=self.other_user,
			date=date(2024, 3, 1),
			saving_goal=Decimal("200.00"),
		)

		Transaction.objects.create(
			user=self.user,
			date=date(2024, 3, 5),
			type="actual",
			name="March salary actual",
			amount=Decimal("2000.00"),
			category=self.income_category,
			monthly_budget=self.march_budget,
		)
		Transaction.objects.create(
			user=self.user,
			date=date(2024, 3, 10),
			type="actual",
			name="Groceries actual",
			amount=Decimal("300.00"),
			category=self.expense_category,
			monthly_budget=self.march_budget,
		)
		Transaction.objects.create(
			user=self.user,
			date=date(2024, 3, 12),
			type="planned",
			name="Salary planned",
			amount=Decimal("50.00"),
			category=self.income_category,
			monthly_budget=self.march_budget,
		)
		Transaction.objects.create(
			user=self.user,
			date=date(2024, 3, 15),
			type="planned",
			name="Dinner planned",
			amount=Decimal("100.00"),
			category=self.expense_category,
			monthly_budget=self.march_budget,
		)
		Transaction.objects.create(
			user=self.other_user,
			date=date(2024, 3, 7),
			type="actual",
			name="Other user expense",
			amount=Decimal("999.00"),
			category=self.other_user_category,
			monthly_budget=self.other_user_budget,
		)

	def test_dashboard_requires_authentication(self):
		response = self.client.get(self.url)

		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_dashboard_returns_expected_payload_for_selected_month(self):
		self.client.force_authenticate(self.user)

		response = self.client.get(self.url, {"year": 2024, "month": 3, "type": "actual"})

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["type"], "actual")
		self.assertEqual(response.data["budget_id"], self.march_budget.id)
		self.assertEqual(response.data["info"], "Budget : March 2024")
		self.assertEqual(response.data["available_years"], [2024])
		self.assertEqual(response.data["available_months"], [3, 4])

		self.assertEqual(response.data["summary"]["income"], "2000.00")
		self.assertEqual(response.data["summary"]["expense"], "300.00")
		self.assertEqual(response.data["summary"]["balance"], "1700.00")

		self.assertEqual(response.data["monthly_status"]["saving_target"], "500.00")
		self.assertEqual(response.data["monthly_status"]["current_saved"], "1700.00")
		self.assertEqual(response.data["monthly_status"]["remaining_to_target"], "-1200.00")
		self.assertEqual(response.data["monthly_status"]["progress_percentage"], "340.00")

		self.assertEqual(len(response.data["categories"]), 1)
		self.assertEqual(response.data["categories"][0]["name"], "food")
		self.assertEqual(response.data["categories"][0]["spent_amount"], "300.00")

	def test_dashboard_invalid_month_returns_400(self):
		self.client.force_authenticate(self.user)

		response = self.client.get(self.url, {"year": 2024, "month": 13})

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(response.data, {"error": "Invalid year or month."})

	def test_dashboard_filters_summary_by_transaction_type(self):
		self.client.force_authenticate(self.user)

		response = self.client.get(self.url, {"year": 2024, "month": 3, "type": "planned"})

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["type"], "planned")
		self.assertEqual(response.data["summary"]["income"], "50.00")
		self.assertEqual(response.data["summary"]["expense"], "100.00")
		self.assertEqual(response.data["summary"]["balance"], "-50.00")

	def test_dashboard_stores_selected_month_in_session(self):
		self.client.force_authenticate(self.user)

		response = self.client.get(self.url, {"year": 2024, "month": 4})

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(self.client.session["selected_dashboard_date"], "2024-04-01")

	def test_dashboard_isolated_to_authenticated_user_data(self):
		self.client.force_authenticate(self.user)

		response = self.client.get(self.url, {"year": 2024, "month": 3, "type": "actual"})

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["summary"]["expense"], "300.00")
