"""
Management command to setup production environment.
This command runs migrations and creates a superuser if needed.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import connection
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'Setup production environment - run migrations and create superuser'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default=os.getenv('SUPERUSER_EMAIL', 'admin@bondah.org'),
            help='Superuser username (email)'
        )
        parser.add_argument(
            '--password',
            type=str,
            default=os.getenv('SUPERUSER_PASSWORD', 'Bondah@admin$$25'),
            help='Superuser password'
        )
        parser.add_argument(
            '--first-name',
            type=str,
            default=os.getenv('SUPERUSER_FIRST_NAME', 'Bondah'),
            help='Superuser first name'
        )
        parser.add_argument(
            '--last-name',
            type=str,
            default=os.getenv('SUPERUSER_LAST_NAME', 'Admin'),
            help='Superuser last name'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Starting production setup...'))
        
        # Step 1: Run migrations
        self.stdout.write('📊 Running database migrations...')
        from django.core.management import call_command
        call_command('migrate', verbosity=0)
        self.stdout.write(self.style.SUCCESS('✅ Migrations completed successfully!'))
        
        # Step 2: Collect static files
        self.stdout.write('📁 Collecting static files...')
        call_command('collectstatic', '--noinput', verbosity=0)
        self.stdout.write(self.style.SUCCESS('✅ Static files collected successfully!'))
        
        # Step 3: Create superuser if it doesn't exist
        username = options['username']
        password = options['password']
        first_name = options['first_name']
        last_name = options['last_name']
        
        if User.objects.filter(email=username).exists():
            self.stdout.write(self.style.WARNING(f'⚠️  Superuser {username} already exists'))
        else:
            self.stdout.write(f'👤 Creating superuser: {username}')
            try:
                user = User.objects.create_superuser(
                    email=username,
                    password=password,
                    first_name=first_name,
                    last_name=last_name
                )
                self.stdout.write(self.style.SUCCESS(f'✅ Superuser {username} created successfully!'))
                self.stdout.write(f'   Email: {username}')
                self.stdout.write(f'   Password: {password}')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error creating superuser: {str(e)}'))
        
        # Step 4: Display setup summary
        self.stdout.write(self.style.SUCCESS('\n🎉 Production setup completed!'))
        self.stdout.write('📋 Summary:')
        self.stdout.write('   ✅ Database migrations applied')
        self.stdout.write('   ✅ Static files collected')
        self.stdout.write('   ✅ Superuser created/verified')
        self.stdout.write('\n🔗 Your API is ready to use!')
        self.stdout.write('   Health check: /health/')
        self.stdout.write('   Admin panel: /admin/')
        self.stdout.write('   API endpoints: /api/')
