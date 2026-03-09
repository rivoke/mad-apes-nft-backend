import logging

import requests
from django.core.management.base import BaseCommand

from user.models import User, UserLootBoxReward
from user.tasks import lootbox_nft_sync


class Command(BaseCommand):
    @staticmethod
    def lootbox_nft_sync():
        lootbox_nft_sync()
    def add_arguments(self, parser):
        """
        :param parser:
        """
        parser.add_argument('command', type=str)

    def handle(self, *args, **options):
        """
        :param args: setup_backend
        :param options: create_admin, all
        """
        command = options['command']
        logging.info(f'Initiating the command {command}...')

        if command == 'lootbox_nft_sync':
            self.lootbox_nft_sync()
        else:
            raise ValueError('Invalid command')
        logging.info('Command completed!')
