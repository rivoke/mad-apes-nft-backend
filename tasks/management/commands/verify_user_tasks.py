from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.db import transaction
from datetime import timedelta
from tasks.models import UserSocialTask


class Command(BaseCommand):
    help = "Verify all unverified user tasks and award food items"

    def handle(self, *args, **kwargs):
        # Get all unverified tasks (timing handled by cron schedule)
        tasks_to_verify = UserSocialTask.objects.filter(
            verified=False
        ).select_related('user', 'task', 'task__food_item')
        
        count = 0
        skipped = 0
        
        for user_task in tasks_to_verify:
            try:
                with transaction.atomic():
                    # Check if already verified (race condition protection)
                    user_task.refresh_from_db()
                    if user_task.verified:
                        skipped += 1
                        self.stdout.write(
                            self.style.WARNING(f"Task {user_task.id} already verified, skipping")
                        )
                        continue
                    
                    # Mark as verified first
                    user_task.verified = True
                    user_task.save(update_fields=['verified'])
                    
                    # Award food item to user's inventory
                    food_item = user_task.task.food_item
                    quantity = user_task.task.quantity
                    
                    # Add food items to inventory
                    # Points will be awarded later when user consumes the food
                    user_task.user.add_food_to_inventory(food_item, quantity)
                    
                    count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Verified task {user_task.id}: {user_task.user.email or user_task.user.username} - "
                            f"Awarded {quantity} {food_item.display_name} to inventory"
                        )
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Error verifying task {user_task.id}: {e}")
                )
                continue
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'='*60}\n"
                f"Summary:\n"
                f"  ✅ Successfully verified: {count} tasks\n"
                f"  ⏭️  Skipped (already verified): {skipped} tasks\n"
                f"{'='*60}"
            )
        )
