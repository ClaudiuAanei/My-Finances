from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from finances.models.budget import MonthlyBudget
from finances.models.categories import Category, CategoryLimit


class CategoryViewTests(APITestCase):
	def setUp(self):
		self.user = User.objects.create_user(username="categories-user", password="password")
		self.other_user = User.objects.create_user(username="other-user", password="password")
		self.url = reverse("categories-list")

		self.expense_category = Category.objects.create(name="food", type="expense")
		self.expense_category.users.add(self.user)

		self.income_category = Category.objects.create(name="salary", type="income")
		self.income_category.users.add(self.user)

		self.budget_march = MonthlyBudget.objects.create(
			user=self.user,
			date=date(2024, 3, 1),
			saving_goal=Decimal("500.00"),
		)
		self.budget_april = MonthlyBudget.objects.create(
			user=self.user,
			date=date(2024, 4, 1),
			saving_goal=Decimal("700.00"),
		)

		CategoryLimit.objects.create(
			user=self.user,
			category=self.expense_category,
			monthly_budget=self.budget_march,
			limit_amount=Decimal("350.00"),
		)
		self.latest_limit = CategoryLimit.objects.create(
			user=self.user,
			category=self.expense_category,
			monthly_budget=self.budget_april,
			limit_amount=Decimal("500.00"),
		)

	def test_list_categories_requires_authentication(self):
		response = self.client.get(self.url)

		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_list_categories_excludes_income_and_returns_latest_limit(self):
		self.client.force_authenticate(self.user)

		response = self.client.get(self.url, {"year": 2024, "month": 4})
		results = response.data["results"]

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["count"], 1)
		self.assertEqual(len(results), 1)
		self.assertEqual(results[0]["name"], "food")
		self.assertEqual(results[0]["type"], "expense")
		self.assertEqual(results[0]["limit_id"], self.latest_limit.id)
		self.assertEqual(results[0]["limit_amount"], "500.00")

	def test_create_category_normalizes_name_and_reuses_existing_category(self):
		self.client.force_authenticate(self.user)

		payload = {"name": "  Travel  ", "type": "expense"}
		first_response = self.client.post(self.url, payload, format="json")
		second_response = self.client.post(self.url, payload, format="json")

		self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(second_response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(first_response.data["id"], second_response.data["id"])

		category = Category.objects.get(id=first_response.data["id"])
		self.assertEqual(category.name, "travel")
		self.assertEqual(Category.objects.filter(name="travel", type="expense").count(), 1)
		self.assertTrue(category.users.filter(id=self.user.id).exists())


class CategoryLimitViewTests(APITestCase):
	def setUp(self):
		self.user = User.objects.create_user(username="limits-user", password="password")
		self.other_user = User.objects.create_user(username="other-user", password="password")

		self.user_category = Category.objects.create(name="groceries", type="expense")
		self.user_category.users.add(self.user)

		self.user_second_category = Category.objects.create(name="transport", type="expense")
		self.user_second_category.users.add(self.user)

		self.other_user_category = Category.objects.create(name="travel", type="expense")
		self.other_user_category.users.add(self.other_user)

		self.user_budget = MonthlyBudget.objects.create(
			user=self.user,
			date=date(2024, 3, 1),
			saving_goal=Decimal("300.00"),
		)
		self.other_user_budget = MonthlyBudget.objects.create(
			user=self.other_user,
			date=date(2024, 3, 1),
			saving_goal=Decimal("100.00"),
		)

		self.existing_limit = CategoryLimit.objects.create(
			user=self.user,
			category=self.user_category,
			monthly_budget=self.user_budget,
			limit_amount=Decimal("250.00"),
		)
		CategoryLimit.objects.create(
			user=self.user,
			category=self.user_second_category,
			monthly_budget=self.user_budget,
			limit_amount=Decimal("120.00"),
		)

	def test_list_limits_returns_only_selected_category_limits(self):
		self.client.force_authenticate(self.user)
		url = reverse("category-limits-list", kwargs={"pk": self.user_category.id})

		response = self.client.get(url)
		results = response.data["results"]

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["count"], 1)
		self.assertEqual(len(results), 1)
		self.assertEqual(results[0]["id"], self.existing_limit.id)
		self.assertEqual(results[0]["category_name"], "groceries")

	def test_create_limit_creates_or_updates_single_limit_for_category_and_budget(self):
		self.client.force_authenticate(self.user)
		url = reverse("category-limits-list", kwargs={"pk": self.user_category.id})

		payload = {
			"category": self.user_category.id,
			"monthly_budget": self.user_budget.id,
			"limit": "400.00",
		}
		response = self.client.post(url, payload, format="json")

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(
			CategoryLimit.objects.filter(
				user=self.user,
				category=self.user_category,
				monthly_budget=self.user_budget,
			).count(),
			1,
		)

		self.existing_limit.refresh_from_db()
		self.assertEqual(self.existing_limit.limit_amount, Decimal("400.00"))

	def test_create_limit_rejects_category_or_budget_not_owned_by_user(self):
		self.client.force_authenticate(self.user)
		url = reverse("category-limits-list", kwargs={"pk": self.user_category.id})

		payload = {
			"category": self.other_user_category.id,
			"monthly_budget": self.other_user_budget.id,
			"limit": "150.00",
		}
		response = self.client.post(url, payload, format="json")

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn("category", response.data)
		self.assertIn("monthly_budget", response.data)
		self.assertEqual(
			CategoryLimit.objects.filter(
				user=self.user,
				category=self.other_user_category,
				monthly_budget=self.other_user_budget,
			).count(),
			0,
		)

	def test_patch_limit_updates_amount(self):
		self.client.force_authenticate(self.user)
		url = reverse(
			"category-limits-detail",
			kwargs={"pk": self.user_category.id, "limit_pk": self.existing_limit.id},
		)

		response = self.client.patch(url, {"limit": "275.00"}, format="json")

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.existing_limit.refresh_from_db()
		self.assertEqual(self.existing_limit.limit_amount, Decimal("275.00"))
