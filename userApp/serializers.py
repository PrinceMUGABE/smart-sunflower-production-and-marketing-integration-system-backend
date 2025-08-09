from rest_framework import serializers
from .models import CustomUser
from django.core.mail import send_mail



from django.contrib.auth import authenticate
from rest_framework import serializers


class ContactUsSerializer(serializers.Serializer):
    names = serializers.CharField(max_length=100, required=True)
    email = serializers.EmailField(required=True)
    subject = serializers.CharField(max_length=255, required=True)
    description = serializers.CharField(required=True)