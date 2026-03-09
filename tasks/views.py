import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from common.permissions import IsValidated
from common.utils import CommonUtils
from .models import SocialTask, UserSocialTask
from .serializers import SocialTaskListSerializer

logger = logging.getLogger(__name__)
from django.db import IntegrityError


class SocialTaskListView(APIView):
    permission_classes = (IsValidated,)

    def get(self, request):
        tasks = (
            SocialTask.objects
            .filter(active=True)
            .select_related("food_item")
            .order_by("-created_at")
        )

        status_map = {}

        if request.user.is_authenticated:
            user_tasks = (
                UserSocialTask.objects
                .filter(user=request.user, task__active=True)
                .only("id", "task_id", "verified", "created_at")
            )

            status_map = {
                ut.task_id: {
                    "started": True,
                    "verified": ut.verified,
                    "user_task_id": ut.id,
                    "started_at": ut.created_at,
                }
                for ut in user_tasks
            }

        serializer = SocialTaskListSerializer(
            tasks,
            many=True,
            context={"status_map": status_map},
        )

        return CommonUtils.dispatch_success(serializer.data)


class UserSocialTaskView(APIView):
    permission_classes = (IsValidated,)

    def post(self, request):
        user = request.user
        task_id = request.data.get("task")

        if not task_id:
            return Response(
                {
                    "status": "error",
                    "message": "task is required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            task = (
                SocialTask.objects
                .select_related("food_item")
                .get(id=task_id, active=True)
            )
        except SocialTask.DoesNotExist:
            return Response(
                {
                    "status": "error",
                    "message": "Task not found or inactive",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            with transaction.atomic():
                user_task, created = UserSocialTask.objects.get_or_create(
                    user=user,
                    task=task,
                    defaults={
                        "verified": task.type == "DAILY_LOGIN_REWARD",
                    },
                )

                if not created:
                    return Response(
                        {
                            "status": "error",
                            "message": "You have already started this task",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if user_task.verified:
                    user.add_food_to_inventory(task.food_item, task.quantity)
                    logger.info(
                        "[TaskStart] Auto-verified daily task for user %s, awarded %s %s",
                        user.id,
                        task.quantity,
                        task.food_item.display_name,
                    )

        except IntegrityError:
            return Response(
                {
                    "status": "error",
                    "message": "You have already started this task",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return CommonUtils.dispatch_success(
            {
                "message": (
                    "Task claimed and verified"
                    if user_task.verified
                    else "Task started successfully"
                ),
                "user_task": {
                    "id": user_task.id,
                    "task_id": task.id,
                    "verified": user_task.verified,
                    "created_at": user_task.created_at,
                },
            },
            status_code=status.HTTP_201_CREATED,
        )
