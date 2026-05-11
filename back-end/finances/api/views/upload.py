from rest_framework import viewsets, permissions
from rest_framework.response import Response
from finances.api.serializers.upload import FileUploadSerializer
from rest_framework.parsers import MultiPartParser, FormParser

class UploadView(viewsets.ViewSet):
    serializer_class = FileUploadSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def create(self, request, *args, **kwargs):
        # Validate the uploaded file using the FileUploadSerializer
        serializer_file = self.serializer_class(data=request.data, context={"request": request})

        if not serializer_file.is_valid():
            return Response(serializer_file.errors, status=400)

        result = serializer_file.save()

        return Response(
            {
                "message": "File uploaded and processed successfully.",
                "processed_count": result.get("processed_count", 0),
                "duplicates_count": result.get("duplicates", 0),
                "duplicates_data": result.get("duplicates_data", [])
            },
            status=200,
        )
