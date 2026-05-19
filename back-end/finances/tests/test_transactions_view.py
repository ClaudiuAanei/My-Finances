from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from finances.models.budget import MonthlyBudget
from finances.models.categories import Category
from finances.models.transactions import Transaction


class TransactionsViewTests(APITestCase):
	def setUp(self):
		self.user = User.objects.create_user(username="transactions-user", password="password")
		self.other_user = User.objects.create_user(username="other-user", password="password")
		self.url = reverse("transactions-list")

		self.category = Category.objects.create(name="groceries", type="expense")
		self.category.users.add(self.user)

		self.other_user_category = Category.objects.create(name="travel", type="expense")
		self.other_user_category.users.add(self.other_user)

	def test_create_transaction_auto_creates_monthly_budget(self):
		self.client.force_authenticate(self.user)
		payload = {
			"name": "Supermarket",
			"type": "actual",
			"amount": "42.50",
			"currency": "EUR",
			"category": self.category.id,
			"date": "2026-05-19",
			"description": "Weekly groceries",
		}

		self.assertFalse(
			MonthlyBudget.objects.filter(user=self.user, date=date(2026, 5, 1)).exists()
		)

		response = self.client.post(self.url, payload, format="json")

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)

		monthly_budget = MonthlyBudget.objects.get(user=self.user, date=date(2026, 5, 1))
		transaction = Transaction.objects.get(id=response.data["id"])

		self.assertEqual(transaction.monthly_budget_id, monthly_budget.id)
		self.assertEqual(transaction.user_id, self.user.id)
		self.assertEqual(transaction.amount, Decimal("42.50"))

	def test_create_transaction_rejects_category_not_assigned_to_user(self):
		self.client.force_authenticate(self.user)
		payload = {
			"name": "Flight",
			"type": "actual",
			"amount": "300.00",
			"currency": "EUR",
			"category": self.other_user_category.id,
			"date": "2026-05-19",
			"description": "Should fail",
		}

		response = self.client.post(self.url, payload, format="json")

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn("category", response.data)
		self.assertEqual(Transaction.objects.filter(user=self.user).count(), 0)
