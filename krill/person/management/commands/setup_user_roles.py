from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from person.models import UserRole, UserPreference

User = get_user_model()


class Command(BaseCommand):
    help = 'Set up UserRole and UserPreference for existing users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update existing roles',
        )

    def handle(self, *args, **options):
        force = options['force']
        
        self.stdout.write('Setting up user roles and preferences...')
        
        users_processed = 0
        roles_created = 0
        roles_updated = 0
        preferences_created = 0
        
        for user in User.objects.all():
            users_processed += 1
            
            # Set up UserRole
            try:
                user_role = user.role
                if force:
                    # Update role based on current user permissions
                    if user.is_superuser and user_role.role != 'lab_admin':
                        user_role.role = 'lab_admin'
                        user_role.save()
                        roles_updated += 1
                        self.stdout.write(f'Updated role for {user.username} to lab_admin')
                    elif not user.is_superuser and user.is_staff and user_role.role == 'viewer':
                        user_role.role = 'lab_manager'
                        user_role.save()
                        roles_updated += 1
                        self.stdout.write(f'Updated role for {user.username} to lab_manager')
            except UserRole.DoesNotExist:
                # Create new role
                if user.is_superuser:
                    role = 'lab_admin'
                elif user.is_staff:
                    role = 'lab_manager'
                else:
                    role = 'viewer'
                
                UserRole.objects.create(
                    user=user,
                    role=role,
                    department='',
                    lab_unit=''
                )
                roles_created += 1
                self.stdout.write(f'Created role for {user.username}: {role}')
            
            # Set up UserPreference
            try:
                user.preference
            except UserPreference.DoesNotExist:
                UserPreference.objects.create(
                    user=user,
                    dark_mode=False
                )
                preferences_created += 1
                self.stdout.write(f'Created preferences for {user.username}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed {users_processed} users:\n'
                f'  - {roles_created} roles created\n'
                f'  - {roles_updated} roles updated\n'
                f'  - {preferences_created} preferences created'
            )
        )
