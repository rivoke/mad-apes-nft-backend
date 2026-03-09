from django.contrib import admin
from .models import SocialTask, UserSocialTask


@admin.register(SocialTask)
class SocialTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'type', 'food_item', 'quantity', 'active', 'created_at')
    list_filter = ('type', 'food_item', 'active', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at',)
    ordering = ['-created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('food_item')


@admin.register(UserSocialTask)
class UserSocialTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'task', 'verified', 'created_at')
    list_filter = ('verified', 'task__type', 'created_at')
    search_fields = ('user__email', 'user__username', 'task__title')
    readonly_fields = ('created_at',)
    ordering = ['-created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'task')