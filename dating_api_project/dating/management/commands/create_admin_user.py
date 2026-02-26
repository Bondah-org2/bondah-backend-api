from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from dating.models import AdminUser

class Command(BaseCommand):
    help = 'Create an admin user for the admin dashboard'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Admin email address')
        parser.add_argument('password', type=str, help='Admin password')

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']
        
        # Check if admin user already exists
        if AdminUser.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.WARNING(f'Admin user with email {email} already exists.')
            )
            return
        
        # Create admin user with hashed password
        admin_user = AdminUser.objects.create(
            email=email,
            password=make_password(password),
            is_active=True
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created admin user: {admin_user.email}')
        )
        self.stdout.write(
            self.style.SUCCESS('You can now use these credentials to login to the admin dashboard.')
        )
