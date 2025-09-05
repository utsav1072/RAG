from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
        ]


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password': "Passwords don't match."})
        validate_password(attrs['password'])
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class DocumentUploadSerializer(serializers.Serializer):
    files = serializers.ListField(
        child=serializers.FileField(), allow_empty=False, write_only=True
    )
    source = serializers.CharField(required=False, allow_blank=True)

    def validate_files(self, value):
        max_size_mb = 20
        for f in value:
            if f.size > max_size_mb * 1024 * 1024:
                raise serializers.ValidationError(
                    f"File {f.name} exceeds {max_size_mb}MB limit."
                )
        return value


class QuerySerializer(serializers.Serializer):
    query = serializers.CharField()
    top_k = serializers.IntegerField(required=False, min_value=1, default=4)
    # Optional simple metadata filter
    source = serializers.CharField(required=False, allow_blank=True)
    generate = serializers.BooleanField(required=False, default=True)
    temperature = serializers.FloatField(required=False, min_value=0.0, max_value=2.0, default=0.7)

