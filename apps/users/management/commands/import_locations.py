import json
import os
from django.core.management.base import BaseCommand
from apps.users.models import Province, City
from django.utils.text import slugify


class Command(BaseCommand):
    help = 'Import states and cities from JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='users/locations/iran_states_cities_formatted.json',
            help='Path to the JSON file (relative to project root)'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        
        # Get the project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        full_path = os.path.join(project_root, file_path)
        
        if not os.path.exists(full_path):
            self.stdout.write(
                self.style.ERROR(f'File not found: {full_path}')
            )
            return
        
        try:
            with open(full_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            self.stdout.write('Starting import...')
            
            # Clear existing data
            City.objects.all().delete()
            Province.objects.all().delete()
            self.stdout.write('Cleared existing states and cities')
            
            states_created = 0
            cities_created = 0
            
            # Handle the JSON structure where states are keys in a dictionary
            for state_key, state_data in data.items():
                state_name = state_data.get('name')
                state_name_en = state_data.get('name_en')
                cities_data = state_data.get('cities', {})
                
                if state_name and state_name_en:
                    state_slug = slugify(f"{state_name_en}")
                    state, created = Province.objects.get_or_create(name=state_name, slug=state_slug)
                    if created:
                        states_created += 1
                    
                    for city_key, city_data in cities_data.items():
                        city_name = city_data.get('name')
                        city_name_en = city_data.get('name_en')
                        if city_name and city_name_en:
                            city_slug = slugify(f"{state_name_en}-{city_name_en}")
                            city, created = City.objects.get_or_create(
                                name=city_name,
                                province=state,
                                slug=city_slug
                            )
                            if created:
                                cities_created += 1
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Import completed successfully!\n'
                    f'Provinces created: {states_created}\n'
                    f'Cities created: {cities_created}'
                )
            )
            
        except json.JSONDecodeError as e:
            self.stdout.write(
                self.style.ERROR(f'Invalid JSON file: {e}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during import: {e}')
            ) 