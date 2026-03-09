from django.dispatch import receiver

from environment.storage import PublicMediaStorage
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models, transaction
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Sum, Value, F
from django.db.models.functions import Coalesce


class FoodItem(models.Model):
    """Defines available food items that can be earned and consumed"""
    FOOD_TYPES = [
        ('FLOWER', 'Flower'),
        ('BANANA', 'Banana'),
    ]

    name = models.CharField(max_length=20, choices=FOOD_TYPES, unique=True)
    display_name = models.CharField(max_length=50)
    points_per_item = models.IntegerField(validators=[MinValueValidator(1)],
                                          help_text="Points awarded when this item is consumed")
    emoji = models.CharField(max_length=10, help_text="Emoji representation of the food item")
    description = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True,db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "food_item"
        verbose_name = 'Food Item'
        verbose_name_plural = 'Food Items'
        ordering = ['name']
        indexes = [
            models.Index(fields=["active", "name"], name="fooditem_active_name_idx"),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.points_per_item} points)"


class FoodInventory(models.Model):
    """User's current food inventory"""
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='food_inventory')
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "food_inventory"
        verbose_name = 'Food Inventory'
        verbose_name_plural = 'Food Inventories'
        unique_together = ['user', 'food_item']
        ordering = ['food_item__name']
        indexes = [
            models.Index(fields=["user", "food_item"], name="foodinv_user_food_idx"),
            models.Index(fields=["user", "last_updated"], name="foodinv_user_updated_idx"),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.food_item.display_name}: {self.quantity}"


class FoodConsumption(models.Model):
    """Track when users consume food items for points"""
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='food_consumptions')
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    quantity_consumed = models.IntegerField(validators=[MinValueValidator(1)])
    points_earned = models.IntegerField(validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "food_consumption"
        verbose_name = 'Food Consumption'
        verbose_name_plural = 'Food Consumptions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["user", "-created_at"], name="foodcons_user_created_idx"),
            models.Index(fields=["food_item"], name="foodcons_food_idx"),
        ]

    def __str__(self):
        return f"{self.user.email} consumed {self.quantity_consumed} {self.food_item.display_name} for {self.points_earned} points"


class ReferralReward(models.Model):
    """Track referral rewards for food items"""
    REWARD_TYPES = [
        ('REFERRAL_SIGNUP', 'Referral Signup Bonus'),
        ('REFERRAL_TASK_COMPLETION', 'Referral Task Completion Bonus'),
    ]

    referrer = models.ForeignKey('User', on_delete=models.CASCADE, related_name='referral_rewards_given')
    referred_user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='referral_rewards_received')
    reward_type = models.CharField(max_length=30, choices=REWARD_TYPES)
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    quantity_awarded = models.IntegerField(validators=[MinValueValidator(1)])
    points_value = models.IntegerField(validators=[MinValueValidator(1)], help_text="Total points value of the reward")
    description = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "referral_reward"
        verbose_name = 'Referral Reward'
        verbose_name_plural = 'Referral Rewards'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["referrer", "-created_at"], name="refreward_referrer_idx"),
            models.Index(fields=["referred_user", "-created_at"], name="refreward_referred_idx"),
            models.Index(fields=["reward_type"], name="refreward_type_idx"),
        ]

    def __str__(self):
        return f"{self.referrer.email} received {self.quantity_awarded} {self.food_item.display_name} for referring {self.referred_user.email}"


class PointsTransaction(models.Model):
    """Track all points awarded to users"""
    TRANSACTION_TYPES = [
        ('SOCIAL_TASK', 'Social Task Completion'),
        ('REFERRAL_BONUS', 'Referral Bonus'),
        ('MANUAL_AWARD', 'Manual Award'),
        ('ADMIN_ADJUSTMENT', 'Admin Adjustment'),
        ('FOOD_CONSUMPTION', 'Food Consumption'),
        ('REFERRAL_FOOD_REWARD', 'Referral Food Reward'),
        ('GAME_SCORE', 'Game Score Submission'),
    ]

    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='points_transactions')
    points = models.IntegerField()
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    description = models.CharField(max_length=200)
    task = models.ForeignKey('tasks.SocialTask', on_delete=models.SET_NULL, null=True, blank=True)
    food_consumption = models.ForeignKey(FoodConsumption, on_delete=models.SET_NULL, null=True, blank=True)
    referral_reward = models.ForeignKey(ReferralReward, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "points_transaction"
        verbose_name = 'Points Transaction'
        verbose_name_plural = 'Points Transactions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.points} points ({self.transaction_type})"


class User(AbstractUser):
    id = models.UUIDField(editable=False, default=uuid.uuid4, primary_key=True)
    full_name = models.CharField(max_length=100, blank=True, null=True)
    referral_rewards_claimed = models.BooleanField(default=False,
                                                   help_text="Whether referral rewards have been claimed")
    last_points_update = models.DateTimeField(auto_now=True)

    # Single-tab session control fields
    wallet_address = models.CharField(max_length=90, null=True, blank=True, db_index=True)
    nickname = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    referral_code = models.CharField(max_length=8, unique=True, null=True, blank=True, db_index=True)
    referred_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referrals',
        editable=False,
        db_index=True,
    )
    total_points = models.IntegerField(default=0, db_index=True)

    first_name = None
    last_name = None

    class Meta:
        db_table = "user"
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=["-total_points", "date_joined"], name="user_points_rank_idx"),
            models.Index(fields=["referred_by"], name="user_referred_by_idx"),
            models.Index(fields=["wallet_address"], name="user_wallet_idx"),
        ]

    def __str__(self):
        return f"{self.email or self.username}"

    @property
    def referral_count(self):
        """Returns the number of users who used this user's referral code"""
        return self.referrals.count()


    def calculate_total_points(self):
        """Calculate total points from all sources"""
        # Points from verified social tasks (quantity * points_per_item)
        verified_tasks = self.social_tasks.filter(verified=True).select_related('task__food_item')
        task_points = sum(
            task.task.quantity * task.task.food_item.points_per_item
            for task in verified_tasks
        )

        # Points from consumed food items
        food_points = self.food_consumptions.aggregate(
            total=Coalesce(Sum('points_earned'), Value(0))
        )['total']

        return (task_points or 0) + (food_points or 0)

    def update_points(self):
        """Update the cached total_points field"""
        self.total_points = self.calculate_total_points()
        self.save(update_fields=['total_points', 'last_points_update'])

    def award_points(self, points, transaction_type, description, task=None, food_consumption=None,
                     referral_reward=None):
        """Award points to user and create transaction record"""
        # Create transaction record
        PointsTransaction.objects.create(
            user=self,
            points=points,
            transaction_type=transaction_type,
            description=description,
            task=task,
            food_consumption=food_consumption,
            referral_reward=referral_reward
        )

        # Update user's total points
        self.update_points()

        return True

    def get_or_create_food_inventory(self, food_item):
        """Get or create food inventory for a specific food item"""
        inventory, created = FoodInventory.objects.get_or_create(
            user=self,
            food_item=food_item,
            defaults={'quantity': 0}
        )
        return inventory

    def add_food_to_inventory(self, food_item, quantity):
        """Add food items to user's inventory"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        inventory = self.get_or_create_food_inventory(food_item)
        inventory.quantity += quantity
        inventory.save()
        return inventory

    def get_food_inventory_summary(self):
        """Get user's complete food inventory summary"""
        inventories = FoodInventory.objects.filter(user=self).select_related('food_item')

        summary = {
            'total_items': 0,
            'items': []
        }

        for inventory in inventories:
            item_data = {
                'food_item': {
                    'id': inventory.food_item.id,
                    'name': inventory.food_item.name,
                    'display_name': inventory.food_item.display_name,
                    'emoji': inventory.food_item.emoji,
                    'points_per_item': inventory.food_item.points_per_item,
                },
                'quantity': inventory.quantity,
                'potential_points': inventory.quantity * inventory.food_item.points_per_item,
                'last_updated': inventory.last_updated.isoformat()
            }
            summary['items'].append(item_data)
            summary['total_items'] += inventory.quantity

        return summary

    def get_consumed_food_points(self):
        """Get total points earned from consuming food"""
        return self.food_consumptions.aggregate(
            total=Coalesce(Sum('points_earned'), Value(0))
        )['total']


# ==================== LOOTBOX SYSTEM MODELS ====================

class LootBox(models.Model):
    id = models.UUIDField(editable=False, default=uuid.uuid4, primary_key=True)
    """Represents a loot box that can be purchased with food items"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(storage=PublicMediaStorage(), null=True, blank=True)
    # Cost to purchase (paid with food items)
    cost_food_item = models.ForeignKey(FoodItem, on_delete=models.PROTECT, related_name='lootboxes_for_sale')
    cost_quantity = models.IntegerField(validators=[MinValueValidator(1)],
                                        help_text="Number of food items required to purchase")

    # Purchase limits and availability
    purchase_limit_per_user = models.IntegerField(null=True, blank=True,
                                                  help_text="Max purchases per user (null = unlimited)")
    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "loot_box"
        verbose_name = 'Loot Box'
        verbose_name_plural = 'Loot Boxes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["is_active", "-created_at"], name="lootbox_active_created_idx"),
            models.Index(fields=["cost_food_item"], name="lootbox_cost_food_idx"),
        ]

    def __str__(self):
        return f"{self.name} (Cost: {self.cost_quantity} {self.cost_food_item.display_name})"

    def get_total_purchases_by_user(self, user):
        """Get total number of times this loot box has been purchased by a user"""
        return UserLootBoxPurchase.objects.filter(
            user=user,
            loot_box=self
        ).aggregate(total=models.Sum('quantity_purchased'))['total'] or 0

    def can_user_purchase(self, user, quantity=1):
        """Check if user can purchase this loot box"""
        if not self.is_active:
            return False, "This loot box is not available"

        # Check purchase limit
        if self.purchase_limit_per_user is not None:
            current_purchases = self.get_total_purchases_by_user(user)
            if current_purchases + quantity > self.purchase_limit_per_user:
                remaining = self.purchase_limit_per_user - current_purchases
                return False, f"Purchase limit exceeded. You can only buy {remaining} more."

        # Check if user has enough food items
        try:
            inventory = FoodInventory.objects.get(user=user, food_item=self.cost_food_item)
            required_amount = self.cost_quantity * quantity
            if inventory.quantity < required_amount:
                return False, f"Insufficient {self.cost_food_item.display_name}. You have {inventory.quantity}, need {required_amount}."
        except FoodInventory.DoesNotExist:
            return False, f"You don't have any {self.cost_food_item.display_name} in your inventory."

        return True, "Can purchase"


RARITY_STATS = {
    "COMMON": {
        "strength": 3,
        "speed": 3,
        "agility": 8,
        "endurance": 3,
        "intelligence": 12,
    },
    "RARE": {
        "strength": 8,
        "speed": 6,
        "agility": 6,
        "endurance": 12,
        "intelligence": 10,
    },
    "EPIC": {
        "strength": 12,
        "speed": 12,
        "agility": 20,
        "endurance": 6,
        "intelligence": 8,
    },
    "LEGENDARY": {
        "strength": 20,
        "speed": 12,
        "agility": 15,
        "endurance": 22,
        "intelligence": 5,
    },
}


class LootBoxReward(models.Model):
    id = models.UUIDField(editable=False, default=uuid.uuid4, primary_key=True)
    """Defines possible rewards from a loot box"""
    RARITY_CHOICES = [
        ('COMMON', 'Common'),
        ('RARE', 'Rare'),
        ('EPIC', 'Epic'),
        ('LEGENDARY', 'Legendary'),
    ]
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=255, null=True, blank=True)
    image = models.ImageField(storage=PublicMediaStorage(), null=True, blank=True)
    loot_box = models.ForeignKey(LootBox, on_delete=models.CASCADE, related_name='rewards')
    reward_food_item = models.ForeignKey(FoodItem, on_delete=models.PROTECT, related_name='lootbox_rewards')

    # Quantity range for this reward
    quantity_min = models.IntegerField(validators=[MinValueValidator(1)], help_text="Minimum quantity that can be won")
    quantity_max = models.IntegerField(validators=[MinValueValidator(1)], help_text="Maximum quantity that can be won")

    # Drop rate (weight-based probability)
    drop_rate = models.FloatField(validators=[MinValueValidator(0.01)],
                                  help_text="Probability weight (higher = more common)")

    # Rarity tier
    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES, default='COMMON')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "loot_box_reward"
        verbose_name = 'Loot Box Reward'
        verbose_name_plural = 'Loot Box Rewards'
        ordering = ['-drop_rate']
        indexes = [
            models.Index(fields=["loot_box", "rarity"], name="lootreward_box_rarity_idx"),
            models.Index(fields=["loot_box", "-drop_rate"], name="lootreward_box_drop_idx"),
        ]

    def __str__(self):
        return f"{self.loot_box.name} - {self.reward_food_item.display_name} ({self.quantity_min}-{self.quantity_max}) [{self.rarity}]"

    def clean(self):
        """Validate that quantity_max >= quantity_min"""
        if self.quantity_max < self.quantity_min:
            raise ValidationError("Maximum quantity must be greater than or equal to minimum quantity")


class UserLootBoxPurchase(models.Model):
    id = models.UUIDField(editable=False, default=uuid.uuid4, primary_key=True)
    """Track loot box purchases by users"""
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='lootbox_purchases')
    loot_box = models.ForeignKey(LootBox, on_delete=models.CASCADE, related_name='purchases')

    quantity_purchased = models.IntegerField(validators=[MinValueValidator(1)], default=1)

    # Cost information (snapshot at purchase time)
    total_cost = models.IntegerField(validators=[MinValueValidator(1)])
    cost_food_item = models.ForeignKey(FoodItem, on_delete=models.PROTECT)

    # Track how many have been opened
    quantity_opened = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_loot_box_purchase"
        verbose_name = 'User Loot Box Purchase'
        verbose_name_plural = 'User Loot Box Purchases'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["user", "loot_box"], name="userlootpurchase_user_box_idx"),
            models.Index(fields=["user", "-created_at"], name="upurchase_user_created_idx"),
        ]

    def __str__(self):
        return f"{self.user.email} purchased {self.quantity_purchased}x {self.loot_box.name}"

    @property
    def quantity_remaining(self):
        """Number of unopened loot boxes from this purchase"""
        return self.quantity_purchased - self.quantity_opened

    @property
    def is_fully_opened(self):
        """Check if all loot boxes from this purchase have been opened"""
        return self.quantity_opened >= self.quantity_purchased


class UserLootBoxReward(models.Model):
    """Track rewards won from opening loot boxes"""
    RARITY_CHOICES = [
        ('COMMON', 'Common'),
        ('RARE', 'Rare'),
        ('EPIC', 'Epic'),
        ('LEGENDARY', 'Legendary'),
    ]

    STATUS_CHOICES = [
        ("user_win", "User Win"),
        ("mint_start", "mint_start"),
        ("error", "error"),
        ("transfer_done", "Transfer Done"),
    ]
    id = models.UUIDField(editable=False, default=uuid.uuid4, primary_key=True)
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='lootbox_rewards')
    loot_box = models.ForeignKey(LootBox, on_delete=models.CASCADE, related_name='user_rewards')
    loot_box_reward = models.ForeignKey(LootBoxReward, on_delete=models.SET_NULL, related_name='rewards', null=True,
                                        blank=True)
    purchase = models.ForeignKey(UserLootBoxPurchase, on_delete=models.CASCADE, related_name='rewards', null=True,
                                 blank=True)
    # Reward details
    reward_food_item = models.ForeignKey(FoodItem, on_delete=models.PROTECT, related_name='won_from_lootboxes')
    quantity_won = models.IntegerField(validators=[MinValueValidator(1)])
    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES)
    opened_at = models.DateTimeField(auto_now_add=True)
    current_owner = models.CharField(max_length=150, null=True, blank=True)
    contract_address = models.CharField(max_length=42, null=True, blank=True, db_index=True)
    token_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="user_win", db_index=True)
    token_meta_uri = models.CharField(max_length=150, null=True, blank=True)
    tx_hash = models.CharField(max_length=255, null=True, blank=True)
    metadata = models.JSONField(blank=True, help_text="metadata", null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_loot_box_reward"
        verbose_name = 'User Loot Box Reward'
        verbose_name_plural = 'User Loot Box Rewards'
        ordering = ['-opened_at']
        indexes = [
            models.Index(fields=["user", "-opened_at"], name="ulootreward_user_opened_idx"),
            models.Index(fields=["loot_box", "-opened_at"], name="ulootreward_box_opened_idx"),
            models.Index(fields=["contract_address", "token_id"], name="ulootreward_contract_token_idx"),
            models.Index(fields=["status"], name="ulootreward_status_idx"),
        ]

    def __str__(self):
        return f"{self.user.email} won {self.quantity_won}x {self.reward_food_item.display_name} ({self.rarity}) from {self.loot_box.name}"


class MintProfile(models.Model):
    id = models.UUIDField(editable=False, default=uuid.uuid4, primary_key=True)
    user = models.OneToOneField('User', on_delete=models.CASCADE, related_name='mint_profile')
    current_owner = models.CharField(max_length=150, null=True, blank=True)
    contract_address = models.CharField(max_length=42, db_index=True)
    token_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    token_meta_uri = models.CharField(max_length=150, null=True, blank=True)
    tx_hash = models.CharField(max_length=255, null=True, blank=True)
    metadata = models.JSONField(blank=True, help_text="metadata", null=True)
    strength = models.IntegerField(default=0)
    speed = models.IntegerField(default=0)
    agility = models.IntegerField(default=0)
    endurance = models.IntegerField(default=0)
    intelligence = models.IntegerField(default=0)
    lootbox_total = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"NFT #{self.token_id} ({self.user.username})"

    class Meta:
        indexes = [
            models.Index(fields=["contract_address", "token_id"], name="mintprofile_contract_token_idx"),
        ]



@receiver(models.signals.pre_save, sender=LootBoxReward)
def delete_old_s3_file_on_update_inv(sender, instance, **kwargs):
    if not instance.pk:  # New instance, no old file to delete
        return
    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    # Check if the file field has changed
    if old_instance.image and old_instance.image != instance.image:
        old_instance.image.delete(save=False)

@receiver(models.signals.pre_save, sender=LootBox)
def delete_old_s3_file_on_update_inv(sender, instance, **kwargs):
    if not instance.pk:  # New instance, no old file to delete
        return
    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    # Check if the file field has changed
    if old_instance.image and old_instance.image != instance.image:
        old_instance.image.delete(save=False)