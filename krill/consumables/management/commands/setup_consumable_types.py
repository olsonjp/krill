from django.core.management.base import BaseCommand
from consumables.models.consumable_type import ConsumableType

CONSUMABLE_TYPES = [
    {
        'name': 'Antibody',
        'category': 'antibody',
        'icon': 'biotech',
        'spec_schema': [
            {'name': 'target', 'label': 'Target', 'type': 'text', 'required': True},
            {'name': 'host', 'label': 'Host Species', 'type': 'choice',
             'choices': ['Rabbit', 'Mouse', 'Rat', 'Goat', 'Chicken', 'Hamster', 'Guinea Pig', 'Other'],
             'required': False},
            {'name': 'clonality', 'label': 'Clonality', 'type': 'choice',
             'choices': ['Monoclonal', 'Polyclonal'], 'required': False},
            {'name': 'clone', 'label': 'Clone', 'type': 'text', 'required': False},
            {'name': 'isotype', 'label': 'Isotype', 'type': 'text', 'required': False},
            {'name': 'conjugate', 'label': 'Conjugate/Fluorophore', 'type': 'text', 'required': False},
            {'name': 'reactivity', 'label': 'Reactivity', 'type': 'text', 'required': False},
            {'name': 'application', 'label': 'Validated Applications', 'type': 'text',
             'required': False, 'help': 'e.g. WB, IHC, FACS'},
            {'name': 'dilution', 'label': 'Recommended Dilution', 'type': 'text', 'required': False},
        ],
    },
    {
        'name': 'Enzyme',
        'category': 'enzyme',
        'icon': 'science',
        'spec_schema': [
            {'name': 'concentration', 'label': 'Concentration (units/µL)', 'type': 'text', 'required': False},
            {'name': 'buffer', 'label': 'Supplied Buffer', 'type': 'text', 'required': False},
            {'name': 'storage_temp', 'label': 'Storage Temperature', 'type': 'text', 'required': False,
             'help': 'e.g. -20°C'},
        ],
    },
    {
        'name': 'Kit',
        'category': 'kit',
        'icon': 'inventory_2',
        'spec_schema': [
            {'name': 'number_of_reactions', 'label': 'Number of Reactions', 'type': 'number', 'required': False},
            {'name': 'storage_temp', 'label': 'Storage Temperature', 'type': 'text', 'required': False},
            {'name': 'components', 'label': 'Key Components', 'type': 'textarea', 'required': False},
        ],
    },
    {
        'name': 'Chemical/Reagent',
        'category': 'chemical',
        'icon': 'water_drop',
        'spec_schema': [
            {'name': 'cas_number', 'label': 'CAS Number', 'type': 'text', 'required': False},
            {'name': 'purity', 'label': 'Purity (%)', 'type': 'text', 'required': False},
            {'name': 'formula', 'label': 'Molecular Formula', 'type': 'text', 'required': False},
            {'name': 'hazard_class', 'label': 'Hazard Class', 'type': 'text', 'required': False},
            {'name': 'storage_temp', 'label': 'Storage Temperature', 'type': 'text', 'required': False},
        ],
    },
    {
        'name': 'Cell Line',
        'category': 'cell_line',
        'icon': 'circle',
        'spec_schema': [
            {'name': 'organism', 'label': 'Organism', 'type': 'text', 'required': False},
            {'name': 'tissue', 'label': 'Tissue/Origin', 'type': 'text', 'required': False},
            {'name': 'passage', 'label': 'Passage Number', 'type': 'number', 'required': False},
            {'name': 'mycoplasma_status', 'label': 'Mycoplasma Status', 'type': 'choice',
             'choices': ['Negative', 'Positive', 'Not Tested'], 'required': False},
        ],
    },
    {
        'name': 'Plasmid',
        'category': 'plasmid',
        'icon': 'donut_large',
        'spec_schema': [
            {'name': 'backbone', 'label': 'Backbone', 'type': 'text', 'required': False},
            {'name': 'resistance', 'label': 'Antibiotic Resistance', 'type': 'text', 'required': False},
            {'name': 'insert', 'label': 'Insert/Gene', 'type': 'text', 'required': False},
            {'name': 'host_strain', 'label': 'Host Strain', 'type': 'text', 'required': False},
        ],
    },
    {
        'name': 'Oligo/Primer',
        'category': 'oligo',
        'icon': 'segment',
        'spec_schema': [
            {'name': 'sequence', 'label': 'Sequence (5\'→3\')', 'type': 'textarea', 'required': False},
            {'name': 'tm', 'label': 'Melting Temp (°C)', 'type': 'number', 'required': False},
            {'name': 'length', 'label': 'Length (bp)', 'type': 'number', 'required': False},
            {'name': 'modification', 'label': 'Modification', 'type': 'text', 'required': False,
             'help': 'e.g. 5\' FAM, phosphorylation'},
        ],
    },
    {
        'name': 'Plasticware',
        'category': 'plasticware',
        'icon': 'emoji_food_beverage',
        'spec_schema': [
            {'name': 'size', 'label': 'Size/Volume', 'type': 'text', 'required': False,
             'help': 'e.g. 1.5 mL, 15 mL'},
            {'name': 'sterile', 'label': 'Sterile', 'type': 'boolean', 'required': False},
            {'name': 'material', 'label': 'Material', 'type': 'text', 'required': False,
             'help': 'e.g. polypropylene, polystyrene'},
        ],
    },
    {
        'name': 'Media/Buffer',
        'category': 'media',
        'icon': 'opacity',
        'spec_schema': [
            {'name': 'ph', 'label': 'pH', 'type': 'number', 'required': False},
            {'name': 'storage_temp', 'label': 'Storage Temperature', 'type': 'text', 'required': False},
            {'name': 'supplements', 'label': 'Supplements', 'type': 'textarea', 'required': False,
             'help': 'e.g. 10% FBS, pen/strep'},
        ],
    },
    {
        'name': 'Other',
        'category': 'other',
        'icon': 'category',
        'spec_schema': [],
    },
]


class Command(BaseCommand):
    help = 'Set up default consumable types with spec schemas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update existing types',
        )

    def handle(self, *args, **options):
        force = options['force']
        self.stdout.write('Setting up consumable types...')

        created_count = 0
        updated_count = 0

        for type_data in CONSUMABLE_TYPES:
            try:
                ct = ConsumableType.objects.get(name=type_data['name'])
                if force:
                    ct.category = type_data['category']
                    ct.icon = type_data['icon']
                    ct.spec_schema = type_data['spec_schema']
                    ct.save()
                    updated_count += 1
                    self.stdout.write(f'Updated consumable type: {type_data["name"]}')
                else:
                    self.stdout.write(f'Already exists: {type_data["name"]}')
            except ConsumableType.DoesNotExist:
                ConsumableType.objects.create(
                    name=type_data['name'],
                    category=type_data['category'],
                    icon=type_data['icon'],
                    spec_schema=type_data['spec_schema'],
                )
                created_count += 1
                self.stdout.write(f'Created consumable type: {type_data["name"]}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed consumable types:\n'
                f'  - {created_count} created\n'
                f'  - {updated_count} updated'
            )
        )
