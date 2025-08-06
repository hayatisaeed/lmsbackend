from django.core.management.base import BaseCommand
from users.models import EducationalLevel, StudyBranch, Olympiad


class Command(BaseCommand):
    help = 'Set up sample educational data for testing'

    def handle(self, *args, **options):
        self.stdout.write('Setting up sample educational data...')
        
        # Create Educational Levels
        levels_data = [
            {'name': 'Elementary School', 'min_grade': 1, 'max_grade': 6, 'is_high_school': False},
            {'name': 'Middle School', 'min_grade': 7, 'max_grade': 9, 'is_high_school': False},
            {'name': 'High School', 'min_grade': 10, 'max_grade': 12, 'is_high_school': True},
        ]
        
        for level_data in levels_data:
            level, created = EducationalLevel.objects.get_or_create(
                name=level_data['name'],
                defaults=level_data
            )
            if created:
                self.stdout.write(f'Created educational level: {level.name}')
        
        # Create Study Branches for High School
        high_school = EducationalLevel.objects.get(name='High School')
        branches_data = [
            {'name': 'Mathematical', 'level': high_school},
            {'name': 'Humanities', 'level': high_school},
            {'name': 'Experimental Sciences', 'level': high_school},
            {'name': 'Vocational', 'level': high_school},
        ]
        
        for branch_data in branches_data:
            branch, created = StudyBranch.objects.get_or_create(
                name=branch_data['name'],
                level=branch_data['level'],
                defaults=branch_data
            )
            if created:
                self.stdout.write(f'Created study branch: {branch.name}')
        
        # Create Olympiads
        olympiads_data = [
            {'name': 'Mathematics Olympiad', 'olympiad_degree': 5, 'published': True},
            {'name': 'Physics Olympiad', 'olympiad_degree': 5, 'published': True},
            {'name': 'Chemistry Olympiad', 'olympiad_degree': 4, 'published': True},
            {'name': 'Biology Olympiad', 'olympiad_degree': 4, 'published': True},
            {'name': 'Computer Science Olympiad', 'olympiad_degree': 5, 'published': True},
            {'name': 'Astronomy Olympiad', 'olympiad_degree': 3, 'published': True},
            {'name': 'Geography Olympiad', 'olympiad_degree': 2, 'published': True},
            {'name': 'Literature Olympiad', 'olympiad_degree': 3, 'published': True},
        ]
        
        for olympiad_data in olympiads_data:
            olympiad, created = Olympiad.objects.get_or_create(
                name=olympiad_data['name'],
                defaults=olympiad_data
            )
            if created:
                self.stdout.write(f'Created olympiad: {olympiad.name}')
        
        self.stdout.write(
            self.style.SUCCESS('Successfully set up sample educational data!')
        ) 