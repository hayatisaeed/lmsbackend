import os
import shutil
import sys
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection
from django.db.utils import OperationalError
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Completely resets the project by erasing database, migrations, pycache and recreating everything'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting fresh project reset..."))

        try:
            # 1. Drop and recreate database
            self.reset_database()

            # 2. Remove celery beat database
            self.remove_celery_beat_db()

            # 3. Remove all migrations
            self.remove_migrations()

            # 4. Remove all pycache directories
            self.remove_pycache()

            # 5. Make new migrations and migrate
            self.make_migrations()

            # 6. Create superuser
            self.create_superuser()

            self.stdout.write(self.style.SUCCESS("Successfully reset the project!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during reset: {str(e)}"))
            sys.exit(1)

    def reset_database(self):
        self.stdout.write("Resetting database...")
        db_info = connection.get_connection_params()
        db_name = db_info.get('database')

        if not db_name:
            self.stdout.write(self.style.ERROR("Could not determine database name"))
            return

        try:
            # Close all connections first
            connection.close()

            if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql':
                # Create a new connection to postgres default db to drop our db
                import psycopg2
                conn = psycopg2.connect(
                    dbname='postgres',
                    user=db_info.get('user'),
                    password=db_info.get('password'),
                    host=db_info.get('host'),
                    port=db_info.get('port')
                )
                conn.autocommit = True
                cursor = conn.cursor()
                
                # Terminate all connections to the target db
                cursor.execute(f"""
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = '{db_name}'
                    AND pid <> pg_backend_pid();
                """)
                
                # Drop and recreate database
                cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
                cursor.execute(f"CREATE DATABASE {db_name}")
                cursor.close()
                conn.close()

            elif settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
                db_path = settings.DATABASES['default']['NAME']
                if os.path.exists(db_path):
                    os.unlink(db_path)
                # Create an empty file to ensure directory exists
                open(db_path, 'a').close()

            # Reconnect to the new database
            connection.connect()

            self.stdout.write(self.style.SUCCESS(f"Database {db_name} has been reset"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error resetting database: {str(e)}"))
            raise

    def remove_celery_beat_db(self):
        celery_db_path = getattr(settings, 'CELERY_BEAT_SCHEDULE_FILENAME', None)
        if celery_db_path and os.path.exists(celery_db_path):
            try:
                os.unlink(celery_db_path)
                self.stdout.write(self.style.SUCCESS("Removed celery beat database"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Could not remove celery beat db: {str(e)}"))

    def remove_migrations(self):
        self.stdout.write("Removing all migrations...")
        migrations_dirs = []
        
        # Find all migrations directories
        for root, dirs, files in os.walk(settings.BASE_DIR):
            if 'migrations' in dirs:
                migrations_dir = os.path.join(root, 'migrations')
                migrations_dirs.append(migrations_dir)
        
        # Remove all migration files except __init__.py
        for migrations_dir in migrations_dirs:
            try:
                for item in os.listdir(migrations_dir):
                    item_path = os.path.join(migrations_dir, item)
                    if item != "__init__.py" and os.path.isfile(item_path):
                        os.unlink(item_path)
                        self.stdout.write(f"Removed {item_path}")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Could not clean {migrations_dir}: {str(e)}"))
                continue
        
        self.stdout.write(self.style.SUCCESS("All migrations removed"))

    def remove_pycache(self):
        self.stdout.write("Removing all __pycache__ directories...")
        pycache_dirs = []
        
        for root, dirs, files in os.walk(settings.BASE_DIR):
            for dir in dirs:
                if dir == "__pycache__":
                    pycache_dir = os.path.join(root, dir)
                    pycache_dirs.append(pycache_dir)
        
        for pycache_dir in pycache_dirs:
            try:
                shutil.rmtree(pycache_dir)
                self.stdout.write(f"Removed {pycache_dir}")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Could not remove {pycache_dir}: {str(e)}"))
                continue
        
        self.stdout.write(self.style.SUCCESS("All __pycache__ directories removed"))

    def make_migrations(self):
        self.stdout.write("Creating new migrations...")
        try:
            call_command('makemigrations')
            
            # Ensure the migrations table exists
            from django.db.migrations.recorder import MigrationRecorder
            recorder = MigrationRecorder(connection)
            try:
                recorder.ensure_schema()
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Could not ensure migrations schema: {str(e)}"))
                raise
            
            call_command('migrate')
            self.stdout.write(self.style.SUCCESS("Database migrated"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during migrations: {str(e)}"))
            raise

    def create_superuser(self):
        self.stdout.write("Creating superuser...")
        from django.contrib.auth import get_user_model
        User = get_user_model()

        phone = '09914307462'
        password = 'admin123'
        display_name = "Admin"
        email = 'parsaishash@gmail.com'

        try:
            # Try to get the user by phone or email
            user = User.objects.filter(phone=phone).first()
            if user:
                if user.is_superuser:
                    self.stdout.write(self.style.WARNING("Superuser already exists. Updating password and email."))
                    user.set_password(password)
                    user.email = email
                    user.display_name = display_name
                    user.is_staff = True
                    user.is_superuser = True
                    user.save()
                    self.stdout.write(self.style.SUCCESS(f"Superuser updated: {phone}/{password}"))
                else:
                    self.stdout.write(self.style.WARNING("User with this phone exists but is not superuser. Deleting and recreating."))
                    user.delete()
                    User.objects.create_superuser(phone=phone, email=email, password=password)
                    self.stdout.write(self.style.SUCCESS(f"Superuser created: {phone}/{password}"))
            else:
                User.objects.create_superuser(phone=phone, email=email, display_name=display_name, password=password)
                self.stdout.write(self.style.SUCCESS(f"Superuser created: {phone}/{password}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating superuser: {str(e)}"))
            raise