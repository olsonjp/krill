from django.core.management.base import BaseCommand
from sample.models.aliquot import AliquotDisposition


class Command(BaseCommand):
    help = 'Set up basic aliquot dispositions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update existing dispositions',
        )

    def handle(self, *args, **options):
        force = options['force']
        self.stdout.write('Setting up aliquot dispositions...')
        
        dispositions_data = [
            {
                'name': 'Stored',
                'dispositionType': 'stored',
                'description': 'Tubes stored in freezer'
            },
            {
                'name': 'In Use',
                'dispositionType': 'in_use',
                'description': 'Tubes currently in use'
            },
            {
                'name': 'Exhausted',
                'dispositionType': 'exhausted',
                'description': 'Tubes that have been used up'
            }
        ]
        
        dispositions_created = 0
        dispositions_updated = 0
        
        for disp_data in dispositions_data:
            try:
                disposition = AliquotDisposition.objects.get(name=disp_data['name'])
                if force:
                    disposition.dispositionType = disp_data['dispositionType']
                    disposition.description = disp_data['description']
                    disposition.save()
                    dispositions_updated += 1
                    self.stdout.write(f'Updated disposition: {disp_data["name"]}')
                else:
                    self.stdout.write(f'Disposition already exists: {disp_data["name"]}')
            except AliquotDisposition.DoesNotExist:
                AliquotDisposition.objects.create(**disp_data)
                dispositions_created += 1
                self.stdout.write(f'Created disposition: {disp_data["name"]}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed dispositions:\n'
                f'  - {dispositions_created} dispositions created\n'
                f'  - {dispositions_updated} dispositions updated'
            )
        )
