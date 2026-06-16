"""
Seed realistic example consumables for UI development and demos.

Covers all 10 types, several vendors, two rooms with locations, and a
deliberately varied set of stock states (well-stocked, low, out, expiring
soon, already expired) so every UI badge and filter has something to show.

Idempotent: items matched by name; re-running updates quantity/threshold
only when --force is passed. Locations/vendors/rooms are always
get_or_created so this is safe to run on a shared dev database.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand

from consumables.models.consumable import Consumable
from consumables.models.consumable_type import ConsumableType
from consumables.models.location import ConsumableLocation, ConsumableRoom
from consumables.models.vendor import Vendor


# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

VENDORS = [
    {'name': 'Abcam', 'website': 'https://www.abcam.com'},
    {'name': 'Cell Signaling Technology', 'website': 'https://www.cellsignal.com'},
    {'name': 'New England Biolabs', 'website': 'https://www.neb.com'},
    {'name': 'Thermo Fisher Scientific', 'website': 'https://www.thermofisher.com'},
    {'name': 'Sigma-Aldrich', 'website': 'https://www.sigmaaldrich.com'},
    {'name': 'ATCC', 'website': 'https://www.atcc.org'},
    {'name': 'Integrated DNA Technologies', 'website': 'https://www.idtdna.com'},
    {'name': 'Sarstedt', 'website': 'https://www.sarstedt.com'},
]

ROOMS = [
    {'name': 'Main Lab (Room 212)', 'description': 'Primary bench space and -20°C freezers'},
    {'name': 'Cold Room (Room 214)', 'description': 'Walk-in 4°C cold room'},
]

LOCATIONS = [
    # Main Lab
    ('Main Lab (Room 212)', 'Freezer A (-20°C)', 'freezer'),
    ('Main Lab (Room 212)', 'Freezer B (-80°C)', 'freezer'),
    ('Main Lab (Room 212)', 'Fridge 1 (4°C)', 'fridge'),
    ('Main Lab (Room 212)', 'Cabinet — Plasticware', 'cabinet'),
    ('Main Lab (Room 212)', 'Bench Shelf — Chemicals', 'shelf'),
    # Cold Room
    ('Cold Room (Room 214)', 'Shelf 1 — Media', 'shelf'),
    ('Cold Room (Room 214)', 'Shelf 2 — Enzymes', 'shelf'),
]

TODAY = date.today()

CONSUMABLES = [
    # ---- Antibodies --------------------------------------------------------
    {
        'name': 'Anti-β-Actin (C4)',
        'type': 'Antibody', 'vendor': 'Abcam',
        'catalog_number': 'ab8226', 'lot_number': 'GR3456789-1',
        'location': 'Freezer A (-20°C)',
        'quantity': '3', 'unit': 'µL aliquots', 'low_stock_threshold': '5',
        'expiration_date': TODAY + timedelta(days=365),
        'specs': {
            'target': 'β-Actin', 'host': 'Mouse', 'clonality': 'Monoclonal',
            'clone': 'C4', 'isotype': 'IgG1', 'reactivity': 'Human, Mouse, Rat',
            'application': 'WB, IHC, IF', 'dilution': '1:5000 (WB)',
        },
        'notes': 'Loading control antibody. Works at high dilution.',
    },
    {
        'name': 'Anti-GAPDH (14C10)',
        'type': 'Antibody', 'vendor': 'Cell Signaling Technology',
        'catalog_number': '2118S', 'lot_number': '12',
        'location': 'Freezer A (-20°C)',
        'quantity': '100', 'unit': 'µL', 'low_stock_threshold': '20',
        'expiration_date': TODAY + timedelta(days=540),
        'specs': {
            'target': 'GAPDH', 'host': 'Rabbit', 'clonality': 'Monoclonal',
            'clone': '14C10', 'isotype': 'IgG', 'reactivity': 'Human, Mouse, Rat',
            'application': 'WB, IHC, IP', 'dilution': '1:1000 (WB)',
        },
    },
    {
        'name': 'Anti-p53 (DO-7)',
        'type': 'Antibody', 'vendor': 'Abcam',
        'catalog_number': 'ab1001', 'lot_number': 'GR9922-2',
        'location': 'Freezer A (-20°C)',
        'quantity': '0', 'unit': 'µL',
        'expiration_date': TODAY + timedelta(days=200),
        'specs': {
            'target': 'p53 (TP53)', 'host': 'Mouse', 'clonality': 'Monoclonal',
            'clone': 'DO-7', 'reactivity': 'Human',
            'application': 'WB, IHC-P, Flow', 'dilution': '1:200',
        },
        'notes': 'Out of stock — reorder pending.',
    },
    {
        'name': 'Anti-Ki67 (SP6)',
        'type': 'Antibody', 'vendor': 'Abcam',
        'catalog_number': 'ab16667',
        'location': 'Freezer A (-20°C)',
        'quantity': '50', 'unit': 'µL', 'low_stock_threshold': '10',
        'expiration_date': TODAY + timedelta(days=15),  # expiring soon
        'specs': {
            'target': 'Ki67', 'host': 'Rabbit', 'clonality': 'Monoclonal',
            'clone': 'SP6', 'reactivity': 'Human, Mouse',
            'application': 'IHC-P, IF', 'dilution': '1:100–1:400',
        },
        'notes': 'Proliferation marker. Expiring soon — check before use.',
    },
    {
        'name': 'Anti-Phospho-Histone H3 (Ser10)',
        'type': 'Antibody', 'vendor': 'Cell Signaling Technology',
        'catalog_number': '9701S',
        'location': 'Freezer A (-20°C)',
        'quantity': '200', 'unit': 'µL', 'low_stock_threshold': '25',
        'expiration_date': TODAY + timedelta(days=730),
        'specs': {
            'target': 'Phospho-Histone H3 (Ser10)', 'host': 'Rabbit',
            'clonality': 'Polyclonal', 'reactivity': 'Human, Mouse, Rat, Hamster, D. melanogaster',
            'application': 'WB, IF, Flow', 'dilution': '1:200',
        },
    },
    # ---- Enzymes -----------------------------------------------------------
    {
        'name': 'EcoRI-HF',
        'type': 'Enzyme', 'vendor': 'New England Biolabs',
        'catalog_number': 'R3101S', 'lot_number': '10131902',
        'location': 'Shelf 2 — Enzymes',
        'quantity': '2', 'unit': 'vials', 'low_stock_threshold': '3',  # low stock
        'expiration_date': TODAY + timedelta(days=400),
        'specs': {'concentration': '20', 'buffer': 'CutSmart', 'storage_temp': '-20°C'},
    },
    {
        'name': 'BamHI-HF',
        'type': 'Enzyme', 'vendor': 'New England Biolabs',
        'catalog_number': 'R3136S',
        'location': 'Shelf 2 — Enzymes',
        'quantity': '10', 'unit': 'vials', 'low_stock_threshold': '2',
        'expiration_date': TODAY + timedelta(days=500),
        'specs': {'concentration': '20', 'buffer': 'CutSmart', 'storage_temp': '-20°C'},
    },
    {
        'name': 'T4 DNA Ligase',
        'type': 'Enzyme', 'vendor': 'New England Biolabs',
        'catalog_number': 'M0202S',
        'location': 'Shelf 2 — Enzymes',
        'quantity': '1', 'unit': 'vials', 'low_stock_threshold': '2',  # low stock
        'expiration_date': TODAY + timedelta(days=300),
        'specs': {'concentration': '400', 'buffer': 'T4 DNA Ligase Buffer 10×', 'storage_temp': '-20°C'},
    },
    {
        'name': 'Proteinase K Solution',
        'type': 'Enzyme', 'vendor': 'Thermo Fisher Scientific',
        'catalog_number': 'AM2546',
        'location': 'Fridge 1 (4°C)',
        'quantity': '5', 'unit': 'mL', 'low_stock_threshold': '2',
        'specs': {'concentration': '20 mg/mL', 'storage_temp': '-20°C or 4°C'},
        'expiration_date': TODAY - timedelta(days=10),  # expired
    },
    # ---- Kits --------------------------------------------------------------
    {
        'name': 'QIAamp DNA Mini Kit',
        'type': 'Kit', 'vendor': 'Sigma-Aldrich',
        'catalog_number': '51304',
        'location': 'Fridge 1 (4°C)',
        'quantity': '3', 'unit': 'kits (50 rxn)', 'low_stock_threshold': '1',
        'expiration_date': TODAY + timedelta(days=365),
        'specs': {'number_of_reactions': '50', 'storage_temp': '15–25°C',
                  'components': 'QIAamp Mini spin columns, Buffer AL, Buffer AW1, Buffer AW2, Buffer AE, Proteinase K'},
    },
    {
        'name': 'RNeasy Mini Kit',
        'type': 'Kit', 'vendor': 'Sigma-Aldrich',
        'catalog_number': '74104',
        'location': 'Fridge 1 (4°C)',
        'quantity': '0', 'unit': 'kits (50 rxn)',  # out of stock
        'expiration_date': TODAY + timedelta(days=180),
        'specs': {'number_of_reactions': '50', 'storage_temp': '15–25°C',
                  'components': 'RNeasy Mini spin columns, Buffer RLT, Buffer RW1, Buffer RPE, RNase-free water'},
        'notes': 'Out of stock. Order immediately — needed for RNA-seq prep.',
    },
    {
        'name': 'Pierce BCA Protein Assay Kit',
        'type': 'Kit', 'vendor': 'Thermo Fisher Scientific',
        'catalog_number': '23225',
        'location': 'Cabinet — Plasticware',
        'quantity': '4', 'unit': 'kits (500 rxn)', 'low_stock_threshold': '1',
        'expiration_date': TODAY + timedelta(days=270),
        'specs': {'number_of_reactions': '500', 'storage_temp': 'RT',
                  'components': 'BCA Reagent A, BCA Reagent B, BSA standards'},
    },
    # ---- Chemicals ---------------------------------------------------------
    {
        'name': 'Tris base',
        'type': 'Chemical/Reagent', 'vendor': 'Sigma-Aldrich',
        'catalog_number': 'T1503',
        'location': 'Bench Shelf — Chemicals',
        'quantity': '450', 'unit': 'g', 'low_stock_threshold': '100',
        'specs': {'cas_number': '77-86-1', 'purity': '≥99.9%', 'formula': 'C4H11NO3',
                  'hazard_class': 'Non-hazardous', 'storage_temp': 'RT'},
    },
    {
        'name': 'Ethanol, 200 proof',
        'type': 'Chemical/Reagent', 'vendor': 'Sigma-Aldrich',
        'catalog_number': '459836',
        'location': 'Bench Shelf — Chemicals',
        'quantity': '2', 'unit': 'L', 'low_stock_threshold': '1',
        'specs': {'cas_number': '64-17-5', 'purity': '≥99.5%', 'formula': 'C2H5OH',
                  'hazard_class': 'Flammable liquid (Cat. 2)', 'storage_temp': 'RT, away from ignition'},
    },
    {
        'name': 'β-Mercaptoethanol',
        'type': 'Chemical/Reagent', 'vendor': 'Sigma-Aldrich',
        'catalog_number': 'M6250',
        'location': 'Freezer A (-20°C)',
        'quantity': '25', 'unit': 'mL', 'low_stock_threshold': '5',
        'specs': {'cas_number': '60-24-2', 'purity': '≥99%', 'formula': 'C2H6OS',
                  'hazard_class': 'Toxic, flammable', 'storage_temp': '2–8°C'},
        'notes': 'Use in fume hood. Highly toxic and volatile.',
    },
    {
        'name': 'DMSO',
        'type': 'Chemical/Reagent', 'vendor': 'Sigma-Aldrich',
        'catalog_number': 'D8418',
        'location': 'Bench Shelf — Chemicals',
        'quantity': '500', 'unit': 'mL', 'low_stock_threshold': '50',
        'specs': {'cas_number': '67-68-5', 'purity': '≥99.9%', 'formula': 'C2H6OS',
                  'storage_temp': 'RT'},
    },
    # ---- Cell lines --------------------------------------------------------
    {
        'name': 'HEK293T',
        'type': 'Cell Line', 'vendor': 'ATCC',
        'catalog_number': 'CRL-3216',
        'location': 'Freezer B (-80°C)',
        'quantity': '12', 'unit': 'vials', 'low_stock_threshold': '3',
        'expiration_date': TODAY + timedelta(days=365 * 3),
        'specs': {'organism': 'Human', 'tissue': 'Embryonic kidney',
                  'passage': '18', 'mycoplasma_status': 'Negative'},
    },
    {
        'name': 'MCF-7',
        'type': 'Cell Line', 'vendor': 'ATCC',
        'catalog_number': 'HTB-22',
        'location': 'Freezer B (-80°C)',
        'quantity': '2', 'unit': 'vials', 'low_stock_threshold': '3',  # low stock
        'specs': {'organism': 'Human', 'tissue': 'Breast adenocarcinoma',
                  'passage': '32', 'mycoplasma_status': 'Negative'},
    },
    # ---- Plasmids ----------------------------------------------------------
    {
        'name': 'pLenti-CMV-GFP-Puro',
        'type': 'Plasmid',
        'location': 'Freezer A (-20°C)',
        'quantity': '15', 'unit': 'µg aliquots', 'low_stock_threshold': '3',
        'specs': {'backbone': 'pLenti-CMV', 'resistance': 'Ampicillin (bacteria), Puromycin (mammalian)',
                  'insert': 'EGFP', 'host_strain': 'Stbl3'},
        'notes': 'For stable lentiviral transduction. Keep at -20°C; avoid freeze-thaw cycles.',
    },
    {
        'name': 'pSpCas9(BB)-2A-Puro (PX459)',
        'type': 'Plasmid', 'vendor': 'Thermo Fisher Scientific',
        'catalog_number': 'Addgene #62988',
        'location': 'Freezer A (-20°C)',
        'quantity': '8', 'unit': 'µg aliquots',
        'specs': {'backbone': 'pSpCas9', 'resistance': 'Ampicillin (bacteria), Puromycin (mammalian)',
                  'insert': 'SpCas9, guide RNA scaffold', 'host_strain': 'DH5α'},
    },
    # ---- Oligos ------------------------------------------------------------
    {
        'name': 'GAPDH-F (qPCR forward)',
        'type': 'Oligo/Primer', 'vendor': 'Integrated DNA Technologies',
        'catalog_number': 'IDT-24601-F',
        'location': 'Freezer A (-20°C)',
        'quantity': '3', 'unit': 'nmol', 'low_stock_threshold': '2',
        'specs': {'sequence': 'GTCTCCTCTGACTTCAACAGCG', 'tm': '62', 'length': '22'},
    },
    {
        'name': 'GAPDH-R (qPCR reverse)',
        'type': 'Oligo/Primer', 'vendor': 'Integrated DNA Technologies',
        'catalog_number': 'IDT-24601-R',
        'location': 'Freezer A (-20°C)',
        'quantity': '3', 'unit': 'nmol', 'low_stock_threshold': '2',
        'specs': {'sequence': 'ACCACCCTGTTGCTGTAGCCAA', 'tm': '62', 'length': '22'},
    },
    # ---- Plasticware -------------------------------------------------------
    {
        'name': '1.5 mL Microcentrifuge Tubes',
        'type': 'Plasticware', 'vendor': 'Sarstedt',
        'catalog_number': '72.690.001',
        'location': 'Cabinet — Plasticware',
        'quantity': '3', 'unit': 'bags (500)', 'low_stock_threshold': '5',  # low stock
        'specs': {'size': '1.5 mL', 'sterile': False, 'material': 'Polypropylene'},
    },
    {
        'name': '15 mL Conical Tubes',
        'type': 'Plasticware', 'vendor': 'Sarstedt',
        'catalog_number': '62.554.001',
        'location': 'Cabinet — Plasticware',
        'quantity': '8', 'unit': 'racks (25)',
        'specs': {'size': '15 mL', 'sterile': True, 'material': 'Polypropylene'},
    },
    {
        'name': '50 mL Conical Tubes',
        'type': 'Plasticware', 'vendor': 'Sarstedt',
        'catalog_number': '62.547.004',
        'location': 'Cabinet — Plasticware',
        'quantity': '1', 'unit': 'racks (25)', 'low_stock_threshold': '2',  # low stock
        'specs': {'size': '50 mL', 'sterile': True, 'material': 'Polypropylene'},
    },
    {
        'name': 'Cell Culture Flasks T-75',
        'type': 'Plasticware', 'vendor': 'Sarstedt',
        'catalog_number': '83.3911.302',
        'location': 'Cabinet — Plasticware',
        'quantity': '12', 'unit': 'flasks', 'low_stock_threshold': '4',
        'specs': {'size': 'T-75 (75 cm²)', 'sterile': True, 'material': 'Polystyrene'},
    },
    # ---- Media/Buffer ------------------------------------------------------
    {
        'name': 'DMEM High Glucose',
        'type': 'Media/Buffer', 'vendor': 'Thermo Fisher Scientific',
        'catalog_number': '11965092',
        'location': 'Shelf 1 — Media',
        'quantity': '6', 'unit': 'bottles (500 mL)', 'low_stock_threshold': '2',
        'expiration_date': TODAY + timedelta(days=180),
        'specs': {'storage_temp': '2–8°C', 'supplements': 'Add 10% FBS, 1% pen/strep before use'},
    },
    {
        'name': 'PBS 1× (Phosphate Buffered Saline)',
        'type': 'Media/Buffer', 'vendor': 'Thermo Fisher Scientific',
        'catalog_number': '10010023',
        'location': 'Shelf 1 — Media',
        'quantity': '4', 'unit': 'bottles (500 mL)', 'low_stock_threshold': '2',
        'specs': {'ph': '7.4', 'storage_temp': 'RT or 2–8°C'},
    },
    {
        'name': 'Fetal Bovine Serum (FBS)',
        'type': 'Media/Buffer', 'vendor': 'Thermo Fisher Scientific',
        'catalog_number': '10082147',
        'location': 'Freezer A (-20°C)',
        'quantity': '0', 'unit': 'bottles (500 mL)', 'low_stock_threshold': '2',  # out of stock
        'expiration_date': TODAY + timedelta(days=365),
        'specs': {'storage_temp': '-20°C; thaw at 4°C overnight',
                  'supplements': 'Heat-inactivate 30 min at 56°C before use'},
        'notes': 'Out of stock! Critical reagent.',
    },
    {
        'name': 'Trypsin-EDTA 0.25%',
        'type': 'Media/Buffer', 'vendor': 'Thermo Fisher Scientific',
        'catalog_number': '25200056',
        'location': 'Fridge 1 (4°C)',
        'quantity': '3', 'unit': 'bottles (100 mL)',
        'expiration_date': TODAY + timedelta(days=22),  # expiring soon
        'specs': {'storage_temp': '-20°C (stock) or 4°C (working)', 'ph': '7.2'},
    },
]


class Command(BaseCommand):
    help = 'Seed realistic example consumables for UI development and demos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite quantity and threshold on existing items',
        )

    def handle(self, *args, **options):
        force = options['force']
        self.stdout.write('Seeding example consumables...\n')

        # Vendors
        vendors = {}
        for v in VENDORS:
            obj, created = Vendor.objects.get_or_create(
                name=v['name'], defaults={'website': v.get('website', '')}
            )
            vendors[obj.name] = obj
            self.stdout.write(f"  {'Created' if created else 'Exists '} vendor: {obj.name}")

        # Rooms
        rooms = {}
        for r in ROOMS:
            obj, created = ConsumableRoom.objects.get_or_create(
                name=r['name'], defaults={'description': r.get('description', '')}
            )
            rooms[obj.name] = obj
            self.stdout.write(f"  {'Created' if created else 'Exists '} room: {obj.name}")

        # Locations
        locations = {}
        for room_name, loc_name, kind in LOCATIONS:
            room = rooms[room_name]
            obj, created = ConsumableLocation.objects.get_or_create(
                room=room, name=loc_name, defaults={'kind': kind}
            )
            locations[loc_name] = obj
            self.stdout.write(f"  {'Created' if created else 'Exists '} location: {room_name} / {loc_name}")

        # Types
        types = {ct.name: ct for ct in ConsumableType.objects.all()}

        # Consumables
        self.stdout.write('')
        created_count = updated_count = skipped_count = 0

        for spec in CONSUMABLES:
            ctype = types.get(spec['type'])
            if not ctype:
                self.stdout.write(
                    self.style.WARNING(f"  Skipping '{spec['name']}': type '{spec['type']}' not found. Run setup_consumable_types first.")
                )
                skipped_count += 1
                continue

            vendor = vendors.get(spec.get('vendor', ''))
            location = locations.get(spec.get('location', ''))

            defaults = {
                'consumable_type': ctype,
                'vendor': vendor,
                'location': location,
                'catalog_number': spec.get('catalog_number', ''),
                'lot_number': spec.get('lot_number', ''),
                'quantity': Decimal(spec.get('quantity', '0')),
                'unit': spec.get('unit', 'units'),
                'low_stock_threshold': Decimal(spec['low_stock_threshold']) if spec.get('low_stock_threshold') else None,
                'expiration_date': spec.get('expiration_date'),
                'specs': spec.get('specs', {}),
                'notes': spec.get('notes', ''),
            }

            obj, created = Consumable.objects.get_or_create(
                name=spec['name'],
                defaults=defaults,
            )

            if created:
                created_count += 1
                stock = '(low stock)' if obj.is_low_stock else '(out)' if obj.is_out_of_stock else ''
                self.stdout.write(f"  Created: {obj.name} — {obj.quantity} {obj.unit} {stock}")
            elif force:
                for k, v in defaults.items():
                    setattr(obj, k, v)
                obj.save()
                updated_count += 1
                self.stdout.write(f"  Updated: {obj.name}")
            else:
                skipped_count += 1
                self.stdout.write(f"  Exists:  {obj.name}")

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done — {created_count} created, {updated_count} updated, {skipped_count} skipped.\n'
            f'Tip: re-run with --force to reset quantities to seed values.'
        ))
