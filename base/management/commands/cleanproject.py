import os
import shutil
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Clean all __pycache__, *.pyc, and migration files (except __init__.py) in mentorhub/config. Optionally flush the DB.'

    def add_arguments(self, parser):
        parser.add_argument('--flush-db', action='store_true', help='Flush the database after cleaning files.')

    def handle(self, *args, **options):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_dir = os.path.join(base_dir, 'config')
        self.stdout.write(self.style.WARNING(f'Cleaning project files in: {config_dir}'))

        # Remove __pycache__ folders
        for root, dirs, files in os.walk(config_dir):
            for d in dirs:
                if d == '__pycache__':
                    pycache_path = os.path.join(root, d)
                    shutil.rmtree(pycache_path, ignore_errors=True)
                    self.stdout.write(self.style.SUCCESS(f'Removed {pycache_path}'))

        # Remove *.pyc files
        for root, dirs, files in os.walk(config_dir):
            for f in files:
                if f.endswith('.pyc'):
                    pyc_path = os.path.join(root, f)
                    os.remove(pyc_path)
                    self.stdout.write(self.style.SUCCESS(f'Removed {pyc_path}'))

        # Remove migration files except __init__.py
        for root, dirs, files in os.walk(config_dir):
            if 'migrations' in root:
                for f in files:
                    if f != '__init__.py' and f.endswith('.py'):
                        migration_path = os.path.join(root, f)
                        os.remove(migration_path)
                        self.stdout.write(self.style.SUCCESS(f'Removed {migration_path}'))

        if options['flush_db']:
            self.stdout.write(self.style.WARNING('Flushing the database...'))
            call_command('flush', interactive=False)
            self.stdout.write(self.style.SUCCESS('Database flushed.'))

        self.stdout.write(self.style.SUCCESS('Cleanup complete.'))