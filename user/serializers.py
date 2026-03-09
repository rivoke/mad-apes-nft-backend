from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import *


class MintProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MintProfile
        fields = "__all__"


class UserShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "nickname", "email")


class UserUpdateSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ("full_name", "nickname", "email")


class UserLookupSerializer(serializers.ModelSerializer):
    mint_profile = MintProfileSerializer(read_only=True)
    referral_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id", "username", "email", "full_name", "nickname",
            "referral_code", "referred_by", "referral_count", "wallet_address", "mint_profile"
        )


class FoodItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodItem
        fields = ("id", "name", "display_name", "emoji", "points_per_item", "description")


class LootBoxListSerializer(serializers.ModelSerializer):
    cost_food_item = FoodItemSerializer(read_only=True)

    class Meta:
        model = LootBox
        fields = '__all__'
