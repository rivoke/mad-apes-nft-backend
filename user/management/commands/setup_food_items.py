from django.core.management.base import BaseCommand
from user.models import FoodItem


class Command(BaseCommand):
    help = 'Setup initial food items for the food inventory system'

    def handle(self, *args, **options):
        self.stdout.write('Setting up food items...')
        
        # Create or update Flower food item
        flower, created = FoodItem.objects.get_or_create(
            name='FLOWER',
            defaults={
                'display_name': 'Flower',
                'points_per_item': 1,
                'emoji': 'flower',
                'description': 'A beautiful flower that gives 1 point when consumed',
                'active': True
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('Created Flower food item'))
        else:
            self.stdout.write('Flower food item already exists')
        
        # Create or update Banana food item
        banana, created = FoodItem.objects.get_or_create(
            name='BANANA',
            defaults={
                'display_name': 'Banana',
                'points_per_item': 1,
                'emoji': 'banana',
                'description': 'A delicious banana that gives 1 point when consumed',
                'active': True
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('Created Banana food item'))
        else:
            self.stdout.write('Banana food item already exists')
        
        self.stdout.write(self.style.SUCCESS('Food items setup completed!'))
        self.stdout.write(f'Available food items:')
        for item in FoodItem.objects.filter(active=True):
            self.stdout.write(f'  - {item.emoji} {item.display_name} ({item.points_per_item} point per item)')
