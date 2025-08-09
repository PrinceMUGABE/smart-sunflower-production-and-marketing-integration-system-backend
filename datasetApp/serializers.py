# serializers.py

from rest_framework import serializers

class DatasetSerializer(serializers.Serializer):
    name = serializers.CharField()
    columns = serializers.ListField(child=serializers.CharField())
    sample_rows = serializers.IntegerField()
    size_bytes = serializers.IntegerField()
    size_human = serializers.CharField()
    last_modified = serializers.DateTimeField()

class DatasetPreviewSerializer(serializers.Serializer):
    total_rows = serializers.IntegerField()
    columns = serializers.ListField(child=serializers.CharField())
    preview = serializers.ListField(child=serializers.DictField())