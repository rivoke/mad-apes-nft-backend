import json
import logging
import random
import time

from django.db import transaction
from django.db.models import F
from .models import LootBox, LootBoxReward, UserLootBoxPurchase, UserLootBoxReward, FoodInventory, PointsTransaction, \
    RARITY_STATS, MintProfile
from .tasks import update_lootbox_nft, process_reward_nft_sync, lootbox_nft_sync

logger = logging.getLogger(__name__)


class LootBoxService:
    """Service layer for loot box operations"""

    @staticmethod
    @transaction.atomic
    def purchase_loot_box(user, loot_box_id, quantity=1):
        """Purchase loot boxes with food items"""
        if quantity < 1:
            raise ValueError("Quantity must be at least 1")

        try:
            loot_box = LootBox.objects.select_for_update().get(id=loot_box_id)
        except LootBox.DoesNotExist:
            raise ValueError("Loot box not found")

        # Check if user can purchase
        can_purchase, message = loot_box.can_user_purchase(user, quantity)
        if not can_purchase:
            raise ValueError(message)

        # Calculate total cost
        total_cost = loot_box.cost_quantity * quantity

        # Deduct food items from user's inventory
        try:
            inventory = FoodInventory.objects.select_for_update().get(
                user=user,
                food_item=loot_box.cost_food_item
            )

            if inventory.quantity < total_cost:
                raise ValueError(f"Insufficient {loot_box.cost_food_item.display_name}")

            inventory.quantity -= total_cost
            inventory.save()

        except FoodInventory.DoesNotExist:
            raise ValueError(f"You don't have any {loot_box.cost_food_item.display_name} in your inventory")

        # Create purchase record
        purchase = UserLootBoxPurchase.objects.create(
            user=user,
            loot_box=loot_box,
            quantity_purchased=quantity,
            total_cost=total_cost,
            cost_food_item=loot_box.cost_food_item
        )

        logger.info(
            f"[LootBox] User {user.email} purchased {quantity}x {loot_box.name} for {total_cost} {loot_box.cost_food_item.display_name}")

        return purchase

    @staticmethod
    @transaction.atomic
    def open_loot_box(user, loot_box_id):
        """Open a loot box and get a random reward"""
        try:
            loot_box = LootBox.objects.get(id=loot_box_id)
        except LootBox.DoesNotExist:
            raise ValueError("Loot box not found")

        purchase = (
            UserLootBoxPurchase.objects
            .select_for_update()
            .filter(user=user, loot_box=loot_box)
            .exclude(quantity_opened__gte=F("quantity_purchased"))
            .first()
        )

        if not purchase:
            raise ValueError("You don't have any unopened loot boxes of this type")

        rewards = list(
            LootBoxReward.objects
            .filter(loot_box=loot_box)
            .select_related("reward_food_item")
        )

        if not rewards:
            raise ValueError("This loot box has no configured rewards")

        weights = [reward.drop_rate for reward in rewards]
        selected_reward = random.choices(rewards, weights=weights, k=1)[0]
        quantity_won = random.randint(selected_reward.quantity_min, selected_reward.quantity_max)

        user.add_food_to_inventory(selected_reward.reward_food_item, quantity_won)

        user_reward = UserLootBoxReward.objects.create(
            user=user,
            loot_box=loot_box,
            loot_box_reward=selected_reward,
            purchase=purchase,
            reward_food_item=selected_reward.reward_food_item,
            quantity_won=quantity_won,
            rarity=selected_reward.rarity,
        )

        stat_increments = RARITY_STATS.get(selected_reward.rarity, {})
        user_update = {k: F(k) + v for k, v in stat_increments.items()}
        user_update["lootbox_total"] = F("lootbox_total") + 1
        MintProfile.objects.filter(user=user).update(**user_update)

        purchase.quantity_opened = F("quantity_opened") + 1
        purchase.save(update_fields=["quantity_opened"])
        process_reward_nft_sync(user_reward.id)

        def enqueue_nft_task():
            try:
                update_lootbox_nft.apply_async(countdown=60)
            except Exception as e:
                time.sleep(60)
                logger.warning(f"Celery unavailable, running task inline: {e}")
                lootbox_nft_sync()

        transaction.on_commit(enqueue_nft_task)

        return user_reward

    @staticmethod
    def get_user_loot_box_inventory(user):
        """Get user's unopened loot boxes"""
        purchases = UserLootBoxPurchase.objects.filter(
            user=user
        ).exclude(
            quantity_opened__gte=F('quantity_purchased')
        ).select_related('loot_box', 'cost_food_item').order_by('-created_at')

        inventory_data = []
        for purchase in purchases:
            inventory_data.append({
                'purchase_id': purchase.id,
                'loot_box': {
                    'id': purchase.loot_box.id,
                    'name': purchase.loot_box.name,
                    'description': purchase.loot_box.description,
                },
                'quantity_remaining': purchase.quantity_remaining,
                'quantity_purchased': purchase.quantity_purchased,
                'quantity_opened': purchase.quantity_opened,
                'purchased_at': purchase.created_at.isoformat(),
            })

        return inventory_data

    @staticmethod
    def get_user_purchase_history(user):
        """Get user's loot box purchase history with rewards"""
        purchases = UserLootBoxPurchase.objects.filter(
            user=user
        ).select_related('loot_box', 'cost_food_item').prefetch_related('rewards',
                                                                        'rewards__reward_food_item').order_by(
            '-created_at')

        history_data = []
        for purchase in purchases:
            # Get rewards for this purchase
            rewards = purchase.rewards.all().select_related('reward_food_item').order_by('-opened_at')
            rewards_data = []

            for reward in rewards:
                rewards_data.append({
                    'id': reward.id,
                    'food_item': {
                        'id': reward.reward_food_item.id,
                        'name': reward.reward_food_item.name,
                        'display_name': reward.reward_food_item.display_name,
                        'emoji': reward.reward_food_item.emoji,
                        'points_per_item': reward.reward_food_item.points_per_item,
                    },
                    'quantity_won': reward.quantity_won,
                    'rarity': reward.rarity,
                    'total_points_value': reward.quantity_won * reward.reward_food_item.points_per_item,
                    'opened_at': reward.opened_at.isoformat(),
                })

            history_data.append({
                'id': purchase.id,
                'loot_box': {
                    'id': purchase.loot_box.id,
                    'name': purchase.loot_box.name,
                },
                'quantity_purchased': purchase.quantity_purchased,
                'quantity_opened': purchase.quantity_opened,
                'quantity_remaining': purchase.quantity_remaining,
                'total_cost': purchase.total_cost,
                'cost_food_item': {
                    'id': purchase.cost_food_item.id,
                    'name': purchase.cost_food_item.name,
                    'display_name': purchase.cost_food_item.display_name,
                    'emoji': purchase.cost_food_item.emoji,
                },
                'is_fully_opened': purchase.is_fully_opened,
                'purchased_at': purchase.created_at.isoformat(),
                'rewards': rewards_data,  # Added: rewards for opened boxes
            })

        return history_data

    @staticmethod
    def get_user_reward_history(user):
        """Get user's loot box reward history"""
        rewards = UserLootBoxReward.objects.filter(
            user=user
        ).select_related('loot_box', 'reward_food_item').order_by('-opened_at')

        history_data = []
        for reward in rewards:
            history_data.append({
                'id': reward.id,
                'loot_box': {
                    'id': reward.loot_box.id,
                    'name': reward.loot_box.name,
                    'image_url': reward.loot_box.image.url if reward.loot_box.image else '',
                },
                'reward': {
                    'food_item': {
                        'id': reward.reward_food_item.id,
                        'name': reward.reward_food_item.name,
                        'display_name': reward.reward_food_item.display_name,
                        'emoji': reward.reward_food_item.emoji,
                        'points_per_item': reward.reward_food_item.points_per_item,
                    },
                    "image": reward.loot_box_reward.image.url if reward.loot_box_reward.image else '',
                    "title": reward.loot_box_reward.title,
                    "metadata": reward.metadata,
                    "token_id": reward.token_id,
                    "contract_address": reward.contract_address,
                    "status": reward.status,
                    'quantity_won': reward.quantity_won,
                    'rarity': reward.rarity,
                    'total_points_value': reward.quantity_won * reward.reward_food_item.points_per_item,
                },
                'opened_at': reward.opened_at.isoformat(),
            })

        return history_data
