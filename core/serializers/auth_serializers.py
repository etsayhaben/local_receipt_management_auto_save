from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from rest_framework import serializers

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['uuid'] = str(user.uuid)
        # Check if the user has any companies
        has_company = user.companies.exists()  # 'companies' is the related_name in CompanyProfile
        token['is_company_created'] = "true" if has_company else "false"
        return token

# serializers.py
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()