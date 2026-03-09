"""
Management command to reset daily tasks
This should be run daily via cron job (e.g., at midnight)

Usage:
    python manage.py reset_daily_tasks
    
Cron job example (runs daily at midnight):
    0 0 * * * cd /path/to/project && python manage.py reset_daily_tasks >> /var/log/daily_tasks.log 2>&1
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from tasks.models import SocialTask, UserSocialTask, SocialTaskType
from user.models import FoodItem


class Command(BaseCommand):
    help = 'Reset daily login reward tasks for all users'

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                # Get the daily reward amount from settings
                daily_reward_amount = getattr(settings, 'DAILY_LOGIN_REWARD_AMOUNT', 10)
                
                # Get the banana food item
                banana_item = FoodItem.objects.filter(name='BANANA', active=True).first()
                
                if not banana_item:
                    self.stdout.write(self.style.ERROR('ERROR: Banana food item not found. Cannot create/reset daily task.'))
                    return
                
                # Get or create the daily login reward task
                daily_task, created = SocialTask.objects.get_or_create(
                    type=SocialTaskType.DAILY_LOGIN_REWARD,
                    defaults={
                        'food_item': banana_item,
                        'quantity': daily_reward_amount,
                        'title': 'Daily Login Reward',
                        'description': f'Claim your daily reward of {daily_reward_amount} bananas!',
                        'link_text': 'Claim Reward',
                        'active': True,
                    }
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f'[SUCCESS] Created daily login reward task: {daily_reward_amount} bananas'))
                else:
                    # Update the quantity in case the environment variable changed
                    if daily_task.quantity != daily_reward_amount:
                        daily_task.quantity = daily_reward_amount
                        daily_task.description = f'Claim your daily reward of {daily_reward_amount} bananas!'
                        daily_task.save()
                        self.stdout.write(self.style.SUCCESS(f'[SUCCESS] Updated daily task reward amount to {daily_reward_amount} bananas'))
                    else:
                        self.stdout.write(self.style.SUCCESS(f'[SUCCESS] Daily task exists: {daily_reward_amount} bananas'))
                
                # Reset all verified user claims for this task (delete them so users can claim again)
                deleted_count = UserSocialTask.objects.filter(
                    task=daily_task,
                    verified=True
                ).delete()[0]
                
                # Also reset unverified claims (clean slate for the day)
                unverified_count = UserSocialTask.objects.filter(
                    task=daily_task,
                    verified=False
                ).delete()[0]
                
                total_reset = deleted_count + unverified_count
                
                self.stdout.write(self.style.SUCCESS(f'[SUCCESS] Reset {deleted_count} verified claims'))
                self.stdout.write(self.style.SUCCESS(f'[SUCCESS] Reset {unverified_count} unverified claims'))
                
                # Summary
                self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
                self.stdout.write(self.style.SUCCESS('Daily Task Reset Complete!'))
                self.stdout.write(self.style.SUCCESS(f'Task: Daily Login Reward'))
                self.stdout.write(self.style.SUCCESS(f'Reward: {daily_reward_amount} bananas'))
                self.stdout.write(self.style.SUCCESS(f'Total Claims Reset: {total_reset} users can now claim again'))
                self.stdout.write(self.style.SUCCESS('=' * 60))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'ERROR: Failed to reset daily tasks: {str(e)}'))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))
            raise

