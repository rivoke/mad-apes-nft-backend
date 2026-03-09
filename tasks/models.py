from django.db import models
from django.conf import settings


class SocialTaskType(models.TextChoices):
    FOLLOW_TWITTER = 'FOLLOW_TWITTER', 'Follow official twitter account'
    JOIN_GARAGE_TELEGRAM = 'JOIN_GARAGE_TELEGRAM', 'Join the Garage telegram'
    LIKE_TWEET = 'LIKE_TWEET', 'Like promotional tweets'
    RETWEET_ANNOUNCEMENT = 'RETWEET_ANNOUNCEMENT', 'Retweet announcements'
    WRITE_THREAD = 'WRITE_THREAD', 'Write an informational thread'
    FOLLOW_INSTAGRAM = 'FOLLOW_INSTAGRAM', 'Follow Instagram account'
    JOIN_DISCORD = 'JOIN_DISCORD', 'Join Discord server'
    SHARE_POST = 'SHARE_POST', 'Share social media post'
    DAILY_LOGIN_REWARD = 'DAILY_LOGIN_REWARD', 'Daily login reward'


class SocialTask(models.Model):
    food_item = models.ForeignKey('user.FoodItem', on_delete=models.PROTECT, related_name='social_tasks')
    quantity = models.IntegerField(default=1)
    type = models.CharField(max_length=30, choices=SocialTaskType.choices)
    title = models.CharField(max_length=150, blank=True, null=True)
    description = models.CharField(max_length=300, blank=True, null=True)
    link_text = models.CharField(max_length=100, blank=True, null=True)
    link = models.CharField(max_length=500, blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "social_task"
        verbose_name = 'Social Task'
        verbose_name_plural = 'Social Tasks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["active", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.title or self.type} - {self.quantity} {self.food_item.display_name if self.food_item else 'items'}"


class UserSocialTask(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='social_tasks')
    task = models.ForeignKey(SocialTask, on_delete=models.CASCADE, related_name='user_tasks')
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_social_task"
        verbose_name = 'User Social Task'
        verbose_name_plural = 'User Social Tasks'
        unique_together = ['user', 'task']  # Prevent duplicate tasks per user
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["user", "task"]),
            models.Index(fields=["user", "verified"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.task.title} ({'Verified' if self.verified else 'Pending'})"