import pandas as pd

from rest_framework import serializers
from datetime import datetime
from finances.services.import_transactions import TransactionImportService


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    month = serializers.IntegerField(required=False)
    year = serializers.IntegerField(required=False)
    
    def validate_file(self, value):
        if not value.name.endswith('.csv'):
            raise serializers.ValidationError({"error": "Only CSV files are allowed."})
        
        try:
            df = pd.read_csv(value, sep=";", decimal=",", nrows=1)
        except pd.errors.EmptyDataError:
            raise serializers.ValidationError({"error": "CSV file is empty."})
        except Exception as e:
            raise serializers.ValidationError({"error": f"Error reading CSV file: {e}"})

        # Reset pointer so the file can be read again in the upload view/processor.
        value.seek(0)

        expected_columns = {"name", "description", "date", "amount", "currency"}
        actual_columns = set(df.columns.str.lower())

        if not expected_columns.issubset(actual_columns):
            missing = expected_columns - actual_columns
            raise serializers.ValidationError({"error": f"CSV file is missing required columns: '{', '.join(missing)}'. "
                                              "Ensure the CSV file contains the following columns: "
                                              "name, description, date, amount, currency."})
        
        return value
    
    def validate_month(self, value):
        if value < 1 or value > 12:
            raise serializers.ValidationError({"error": "Month must be between 1 and 12."})
        return value
    
    def validate_year(self, value):
        now = datetime.now()
        if value < 1900 or value > now.year + 2:
            raise serializers.ValidationError({"error": f"Year must be between 1900 and {now.year + 2}."})
        return value

    def create(self, validated_data):
        request = self.context.get("request")
        
        if request is None:
            raise serializers.ValidationError({"error": "Request context is required."})
        
        now = datetime.now()

        file = validated_data["file"]
        
        month = validated_data.get("month", now.month)
        year = validated_data.get("year", now.year)

        import_service = TransactionImportService(user=request.user, request=request)

        try:
            return import_service.import_csv(file=file, month=month, year=year)
        except ValueError as exc:
            raise serializers.ValidationError({"error": str(exc)})
    
