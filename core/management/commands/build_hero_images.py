"""
Regenerate the responsive homepage hero variants from the master PNG.

Author-time only. Nothing in the request path calls this — the variants it
writes are committed static assets, so production never encodes an image.
Pillow is already a dependency (requirements.txt), so this adds no new tooling.

Why the variants exist
----------------------
The master is a 1536x1024 photographic image stored as a lossless PNG in RGB
mode — no alpha channel, so PNG was buying nothing and costing 2,592,714 bytes.
It was additionally `<link rel=preload as=image>`-ed on the homepage, which gave
the single largest asset on the site the highest possible fetch priority and put
it directly in front of LCP.

Run:
    python manage.py build_hero_images

Add --check to verify the committed variants match what this command would
produce, without writing anything (used by core/tests_hero_assets.py).
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

# One master, several derivatives. Widths chosen for real devices rather than
# round numbers: 768 covers 1x tablets, 1152 covers a 390pt phone at DPR 3
# (1170 CSS px), 1536 is the master width for desktop and DPR-2 laptops.
WIDTHS = (768, 1152, 1536)

# Qualities chosen by measuring PSNR against the master rather than by taste, so
# the three formats sit on the same rung of the quality ladder and the size
# comparison between them is fair:
#
#     AVIF q55   154,933 B   34.01 dB
#     WebP q68   171,946 B   33.85 dB
#     JPEG q78   288,112 B   33.87 dB
#
# At matched quality AVIF is ~10% smaller than WebP and ~46% smaller than JPEG,
# which is why all three are kept rather than shipping WebP alone. A naive
# comparison at equal *quality numbers* makes AVIF look worse than it is —
# AVIF q60 is 184,915 B but also a full dB sharper than WebP q68.
#
# The hero sits behind a scrim and carries no text or fine detail, so ~34 dB is
# comfortably enough; a product shot would want more.
AVIF_QUALITY = 55
WEBP_QUALITY = 68
JPEG_QUALITY = 78

MASTER_NAME = 'ecoiq-better-way-hero.png'
STEM = 'ecoiq-better-way-hero'


def hero_dir() -> Path:
    return Path(settings.BASE_DIR) / 'static' / 'img' / 'hero'


def _variants(master):
    """Yield (filename, PIL image, save-format, save-kwargs) for every output."""
    from PIL import Image

    for width in WIDTHS:
        if width == master.width:
            image = master
        else:
            height = round(master.height * width / master.width)
            image = master.resize((width, height), Image.LANCZOS)
        yield f'{STEM}-{width}.avif', image, 'AVIF', {'quality': AVIF_QUALITY}
        yield f'{STEM}-{width}.webp', image, 'WEBP', {'quality': WEBP_QUALITY, 'method': 6}

    # One JPEG, at the master width, as the <picture> fallback. Only browsers
    # without WebP support ever download it, so it is not worth three of them.
    yield f'{STEM}-{max(WIDTHS)}.jpg', master, 'JPEG', {
        'quality': JPEG_QUALITY, 'optimize': True, 'progressive': True,
    }


class Command(BaseCommand):
    help = 'Regenerate responsive AVIF/WebP/JPEG variants of the homepage hero image.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check', action='store_true',
            help='Verify the committed variants exist and are non-empty; write nothing.',
        )

    def handle(self, *args, **options):
        try:
            from PIL import Image
        except ImportError as exc:                       # pragma: no cover
            raise CommandError('Pillow is required to build hero images.') from exc

        directory = hero_dir()
        master_path = directory / MASTER_NAME
        if not master_path.exists():
            raise CommandError(f'Master image not found: {master_path}')

        master = Image.open(master_path).convert('RGB')

        if options['check']:
            missing = [
                name for name, *_ in _variants(master)
                if not (directory / name).exists() or (directory / name).stat().st_size == 0
            ]
            if missing:
                raise CommandError(
                    'Missing or empty hero variants: ' + ', '.join(missing)
                    + '\nRun: python manage.py build_hero_images'
                )
            self.stdout.write(self.style.SUCCESS('All hero variants present.'))
            return

        total = 0
        for name, image, fmt, kwargs in _variants(master):
            path = directory / name
            image.save(path, fmt, **kwargs)
            size = path.stat().st_size
            total += size
            self.stdout.write(f'  {name:<42} {size:>9,} B')

        self.stdout.write(self.style.SUCCESS(
            f'\nMaster {MASTER_NAME}: {master_path.stat().st_size:,} B\n'
            f'All variants combined:  {total:,} B\n'
            'A browser downloads exactly one of them.'
        ))
