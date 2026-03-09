from django.contrib import admin
from user.models import *
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import Permission


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = UserChangeForm.Meta.fields


class UserAdminView(UserAdmin):
    form = CustomUserChangeForm
    add_form = UserCreationForm
    list_display = (
        'id', 'username', 'email', 'nickname', 'referral_code', 'total_points', 'referral_count', 'referred_by',
        'is_active', "is_superuser",)
    ordering = ("-id",)
    search_fields = ('id', 'username', 'email', 'nickname', 'referral_code')
    readonly_fields = ('referral_code', 'referral_count', 'referred_by', 'total_points', 'last_points_update')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('username', 'full_name', 'nickname')}),
        ('Referral System', {'fields': ('referral_code', 'referred_by', 'referral_count')}),
        ('Points System', {'fields': ('total_points', 'last_points_update')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser',
                                    'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )


@admin.register(PointsTransaction)
class PointsTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'points', 'transaction_type', 'description', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('user__email', 'user__username', 'description')
    readonly_fields = ('created_at',)
    ordering = ['-created_at']


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'display_name', 'emoji', 'points_per_item', 'active', 'created_at')
    list_filter = ('name', 'active', 'created_at')
    search_fields = ('name', 'display_name', 'description')
    readonly_fields = ('created_at',)
    ordering = ['name']
    # Enable autocomplete for lootbox admin
    autocomplete_fields = []


@admin.register(FoodInventory)
class FoodInventoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'food_item', 'quantity', 'last_updated')
    list_filter = ('food_item__name', 'last_updated')
    search_fields = ('user__email', 'user__username', 'food_item__display_name')
    readonly_fields = ('last_updated', 'created_at')
    ordering = ['-last_updated']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'food_item')


@admin.register(FoodConsumption)
class FoodConsumptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'food_item', 'quantity_consumed', 'points_earned', 'created_at')
    list_filter = ('food_item__name', 'created_at')
    search_fields = ('user__email', 'user__username', 'food_item__display_name')
    readonly_fields = ('created_at',)
    ordering = ['-created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'food_item')


@admin.register(ReferralReward)
class ReferralRewardAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'referrer', 'referred_user', 'reward_type', 'food_item', 'quantity_awarded', 'points_value', 'created_at')
    list_filter = ('reward_type', 'food_item__name', 'created_at')
    search_fields = ('referrer__email', 'referrer__username', 'referred_user__email', 'referred_user__username',
                     'food_item__display_name')
    readonly_fields = ('created_at',)
    ordering = ['-created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('referrer', 'referred_user', 'food_item')


admin.site.register(Permission)
admin.site.register(User, UserAdminView)
admin.site.register(MintProfile)


# ==================== LOOTBOX ADMIN ====================

class LootBoxRewardInline(admin.TabularInline):
    """Inline admin for LootBoxReward within LootBox"""
    model = LootBoxReward
    extra = 1
    fields = (
        'title', 'description', 'image', 'reward_food_item', 'quantity_min', 'quantity_max', 'drop_rate', 'rarity')
    autocomplete_fields = ['reward_food_item']


@admin.register(LootBox)
class LootBoxAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'cost_quantity', 'cost_food_item', 'purchase_limit_per_user', 'is_active', 'created_at')
    list_filter = ('is_active', 'cost_food_item__name', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ['-created_at']
    inlines = [LootBoxRewardInline]
    autocomplete_fields = ['cost_food_item']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'image', 'is_active')
        }),
        ('Purchase Cost', {
            'fields': ('cost_food_item', 'cost_quantity', 'purchase_limit_per_user')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('cost_food_item')


@admin.register(LootBoxReward)
class LootBoxRewardAdmin(admin.ModelAdmin):
    list_display = ('id', 'loot_box', 'reward_food_item', 'quantity_min', 'quantity_max', 'drop_rate', 'rarity')
    list_filter = ('rarity', 'loot_box__name', 'reward_food_item__name')
    search_fields = ('loot_box__name', 'reward_food_item__display_name')
    readonly_fields = ('created_at',)
    ordering = ['loot_box', '-drop_rate']
    autocomplete_fields = ['loot_box', 'reward_food_item']

    fieldsets = (
        ('Loot Box', {
            'fields': ('loot_box',)
        }),
        ('Reward Details', {
            'fields': ('title', 'description', 'image', 'reward_food_item', 'quantity_min', 'quantity_max', 'rarity')
        }),
        ('Drop Rate', {
            'fields': ('drop_rate',),
            'description': 'Higher values = more common. Does not need to sum to 100.'
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('loot_box', 'reward_food_item')


@admin.register(UserLootBoxPurchase)
class UserLootBoxPurchaseAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'loot_box', 'quantity_purchased', 'quantity_opened', 'quantity_remaining_display', 'total_cost',
        'cost_food_item', 'created_at')
    list_filter = ('loot_box__name', 'cost_food_item__name', 'created_at')
    search_fields = ('user__email', 'user__username', 'loot_box__name')
    readonly_fields = ('created_at', 'quantity_remaining_display', 'is_fully_opened_display')
    ordering = ['-created_at']
    autocomplete_fields = ['user', 'loot_box', 'cost_food_item']

    fieldsets = (
        ('User & Loot Box', {
            'fields': ('user', 'loot_box')
        }),
        ('Purchase Details', {
            'fields': ('quantity_purchased', 'quantity_opened', 'quantity_remaining_display', 'is_fully_opened_display')
        }),
        ('Cost Information', {
            'fields': ('total_cost', 'cost_food_item')
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def quantity_remaining_display(self, obj):
        return obj.quantity_remaining

    quantity_remaining_display.short_description = 'Quantity Remaining'

    def is_fully_opened_display(self, obj):
        return obj.is_fully_opened

    is_fully_opened_display.short_description = 'Fully Opened'
    is_fully_opened_display.boolean = True

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'loot_box', 'cost_food_item')


@admin.register(UserLootBoxReward)
class UserLootBoxRewardAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'loot_box', 'reward_food_item', 'quantity_won', 'rarity', 'opened_at')
    list_filter = ('rarity', 'loot_box__name', 'reward_food_item__name', 'opened_at')
    search_fields = ('user__email', 'user__username', 'loot_box__name', 'reward_food_item__display_name')
    readonly_fields = ('opened_at',)
    ordering = ['-opened_at']
    autocomplete_fields = ['user', 'loot_box', 'reward_food_item', 'purchase']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'loot_box', 'reward_food_item', 'purchase')
