from rest_framework import serializers

from user.serializers import FoodItemSerializer
from .models import SocialTask, UserSocialTask


class SocialTaskListSerializer(serializers.ModelSerializer):
    total_points = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    food_item = FoodItemSerializer(read_only=True)

    class Meta:
        model = SocialTask
        fields = '__all__'

    def get_total_points(self, obj):
        food_points = getattr(obj.food_item, "points_per_item", 0) or 0
        return obj.quantity * food_points

    def get_status(self, obj):
        status_map = self.context.get("status_map", {})
        return status_map.get(
            obj.id,
            {
                "started": False,
                "verified": False,
                "user_task_id": None,
                "started_at": None,
            },
        )