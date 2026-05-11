import json

import pandas as pd

from KBC.processor import CSVProcessor
from finances.api.serializers.transactions import TransactionSerializer
from finances.models.categories import Category
from finances.services.transaction import TransactionService


class TransactionImportService:
    def __init__(self, user, request):
        self.user = user
        self.request = request
        self._category_cache = {}

    def import_csv(self, file, month, year):
        raw_json = self._extract_csv_json(file=file, month=month, year=year)
        rows = self._parse_rows(raw_json)
        mapped_rows = self._map_category_strings_to_ids(rows)
        validated_transactions = self._validate_transactions(mapped_rows)

        create_result = TransactionService(user=self.user).create_many_transactions(
            transactions_data=validated_transactions,
            raw_transactions_data=mapped_rows,
        )

        return self._build_response(create_result=create_result, total_rows=len(mapped_rows))

    def _extract_csv_json(self, file, month, year):
        try:
            return CSVProcessor(file).get_monthly_json(month, year)
        except pd.errors.EmptyDataError as exc:
            raise ValueError("CSV file is empty.") from exc
        except Exception as exc:
            raise ValueError(f"Failed to process CSV file: {exc}") from exc

    def _parse_rows(self, raw_json):
        try:
            rows = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid file format. Could not decode transactions JSON.") from exc

        if not isinstance(rows, list):
            raise ValueError("Invalid file format. Expected a list of transactions.")

        return rows

    def _map_category_strings_to_ids(self, rows):
        for row in rows:
            category_id = self._resolve_category_id(
                category_value=row.get("category"),
                amount=row.get("amount"),
            )
            row["category"] = category_id

        return rows

    def _resolve_category_id(self, category_value, amount):
        category_name = str(category_value).strip().lower() if category_value else "no category"

        try:
            is_income = float(amount) > 0
        except (TypeError, ValueError):
            is_income = category_name == "income"

        category_type = "income" if is_income else "expense"
        cache_key = (category_name, category_type)

        if cache_key in self._category_cache:
            return self._category_cache[cache_key]

        category = Category.get_or_create_for_user(user=self.user, name=category_name, type=category_type)
        self._category_cache[cache_key] = category.id
        return category.id

    def _validate_transactions(self, rows):
        serializer = TransactionSerializer(data=rows, many=True, context={"request": self.request})

        if not serializer.is_valid():
            raise ValueError(serializer.errors)

        return serializer.validated_data

    @staticmethod
    def _build_response(create_result, total_rows):
        if isinstance(create_result, dict):
            duplicates_count = create_result.get("duplicates_count", 0)
            return {
                "message": f"File processed with {duplicates_count} duplicate transactions skipped.",
                "processed_count": create_result.get("processed_count", 0),
                "duplicates": duplicates_count,
                "duplicates_count": duplicates_count,
                "duplicates_data": create_result.get("duplicates_data", []),
            }

        return {
            "processed_count": total_rows,
            "duplicates": 0,
            "duplicates_count": 0,
            "duplicates_data": [],
        }
