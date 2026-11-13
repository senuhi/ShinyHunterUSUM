"""Language-separated, fail-closed recognition and calibration profiles."""
import hashlib
import json
import math
from pathlib import Path
from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parent
TARGETS = ('poipole', 'typenull_poni', 'typenull_aether')


class SafetyStop(Exception):
    pass


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def roi(image, box):
    if (len(box) != 4 or any(type(v) is not int for v in box) or
        not (0 <= box[0] < box[2] <= image.width and
             0 <= box[1] < box[3] <= image.height)):
        raise SafetyStop(f'Invalid crop {box} for {image.size}')
    return image.crop(box)


def template_score(image, box, template, vertical=0):
    """Normalized grayscale MAE, with only explicit horizontal/vertical search."""
    if not 0 <= vertical <= 8:
        raise SafetyStop('Invalid template vertical search')
    template = template.convert('L')
    if ImageStat.Stat(template).stddev[0] < 5:
        raise SafetyStop('Blank/low-contrast placeholder template')
    best = 1.0
    for dy in range(-vertical, vertical + 1):
        b = [box[0], box[1]+dy, box[2], box[3]+dy]
        crop = roi(image, b).convert('L')
        if template.height != crop.height or template.width > crop.width:
            raise SafetyStop(f'Template {template.size} does not fit ROI {crop.size}')
        for dx in range(crop.width - template.width + 1):
            patch = crop.crop((dx, 0, dx+template.width, template.height))
            best = min(best, ImageStat.Stat(ImageChops.difference(patch, template)).mean[0] / 255)
    return best


def colour_verdict(image, config):
    patch = roi(image, config['box']).convert('RGB')
    mean = ImageStat.Stat(patch).mean
    stddev = max(ImageStat.Stat(patch).stddev)
    refs = [config['normal'], config['shiny']]
    if any(len(r) != 3 or any(not finite(x) or not 0 <= x <= 255 for x in r) for r in refs):
        raise SafetyStop('Invalid colour references')
    distance = lambda a, b: sum((x-y)**2 for x, y in zip(a,b))**0.5
    separation = distance(*refs)
    limits = [config[k] for k in ('max_distance', 'min_margin', 'max_stddev')]
    if (any(not finite(x) or x <= 0 for x in limits) or limits[0] >= 0.5 or
        limits[1] >= 1 or limits[2] > 255 or separation < 10):
        raise SafetyStop('Invalid/overlapping colour thresholds')
    normal, shiny = [distance(mean, ref) / separation for ref in refs]
    margin = abs(normal - shiny)
    result = 'unknown'
    if min(normal, shiny) <= config['max_distance'] and margin >= config['min_margin'] and stddev <= config['max_stddev']:
        result = 'normal' if normal < shiny else 'shiny'
    return dict(verdict=result, mean=mean, normal_distance=normal,
                shiny_distance=shiny, margin=margin, stddev=stddev)


class Profile:
    def __init__(self, language, target, path=None):
        if language not in ('English', 'Japanese') or target not in TARGETS:
            raise SafetyStop('Unsupported game language / gift target')
        self.language, self.target = language, target
        code = {'English':'en', 'Japanese':'ja'}[language]
        self.path = Path(path) if path else ROOT / 'profiles' / f'{code}.json'
        raw = self.path.read_bytes()
        document = json.loads(raw)
        if document['schema'] != 1 or document['language'] != language:
            raise SafetyStop('Profile language/schema mismatch')
        self.data = document['targets'][target]
        self.validate_settings()
        self.assets = (self.path.parent / document['template_root']).resolve()
        self.fingerprint = hashlib.sha256(raw)
        self.templates = {}
        self.missing = []
        self.missing_by_stage = {}
        for name, stage in self.data['stages'].items():
            loaded = []
            for filename in stage['templates']:
                p = (self.assets / filename).resolve()
                if not p.is_relative_to(self.assets):
                    raise SafetyStop('Template path escapes language directory')
                if not p.is_file():
                    self.missing.append(str(p))
                    self.missing_by_stage.setdefault(name, []).append(str(p))
                    continue
                content = p.read_bytes()
                self.fingerprint.update(filename.encode() + content)
                with Image.open(p) as image:
                    template = image.convert('L')
                    if ImageStat.Stat(template).stddev[0] < 5:
                        raise SafetyStop(f'Placeholder/blank template: {p}')
                    loaded.append(template.copy())
            if stage.get('invert'):
                loaded += [ImageChops.invert(t) for t in list(loaded)]
            self.templates[name] = loaded
        self.digest = self.fingerprint.hexdigest()

    def validate_settings(self):
        stages = self.data['stages']
        required = {'dialogue_name', 'menu', 'party_level', 'party_name', 'restart_title', 'save_file'}
        if self.target != 'typenull_poni':
            required.add('party_added')
        if self.target != 'poipole':
            required.add('dialogue_end')
        if not required <= stages.keys():
            raise SafetyStop('Incomplete route stages')
        for name, stage in stages.items():
            if stage['screen'] not in (0, 1):
                raise SafetyStop('Invalid screen')
            size = (320, 240) if stage['screen'] == 0 else (400, 240)
            roi(Image.new('RGB', size), stage['box'])
            if (type(stage.get('attempts', 100)) is not int or
                not 1 <= stage.get('attempts', 100) <= 1000 or
                not finite(stage.get('interval', .1)) or
                not .05 <= stage.get('interval', .1) <= 5 or
                not finite(stage['threshold']) or not 0 < stage['threshold'] <= .2 or
                not stage['templates']):
                raise SafetyStop(f'Invalid stage parameters: {name}')
        fresh = self.data['freshness']
        if (not finite(fresh['max_age']) or not .1 <= fresh['max_age'] <= 5 or
            not finite(fresh['freeze_timeout']) or not .5 <= fresh['freeze_timeout'] <= 120):
            raise SafetyStop('Invalid freshness limits')
        colour = self.data['colour']
        if (colour['screen'] not in (0, 1) or type(colour['samples']) is not int or
            not 3 <= colour['samples'] <= 20 or not finite(colour['sample_interval']) or
            not .05 <= colour['sample_interval'] <= .5):
            raise SafetyStop('Invalid colour consensus parameters')
        colour_verdict(Image.new('RGB', (320 if colour['screen'] == 0 else 400, 240)), colour)
        movement = self.data['approach']
        if (not finite(movement['x']) or not -1 <= movement['x'] <= 1 or
            not finite(movement['seconds']) or not 0 < movement['seconds'] <= 1 or
            type(movement['repeats']) is not int or not 0 <= movement['repeats'] <= 5 or
            not finite(self.data['load_seconds']) or not 0 <= self.data['load_seconds'] <= 15):
            raise SafetyStop('Invalid movement/load timing')

    def require_ready(self, live=False):
        if live and self.missing:
            raise SafetyStop('Missing language templates: ' + ', '.join(self.missing))
        required = ('dialogue_name', 'menu', 'party_level', 'party_name', 'restart_title', 'save_file') if live else ('party_name',)
        for name in required:
            if not self.templates.get(name):
                raise SafetyStop(f'Missing stage: {name}')
        if live:
            receipt = self.path.parent / f'{self.path.stem}-{self.target}.validated.json'
            try:
                validation = json.loads(receipt.read_text())
            except (OSError, ValueError) as e:
                raise SafetyStop('Live mode needs a hardware validation receipt; see docs/CALIBRATION_JA.md') from e
            if (validation.get('profile_sha256') != self.digest or
                validation.get('hardware_verified') is not True or
                validation.get('target') != self.target or
                not validation.get('evidence')):
                raise SafetyStop('Validation receipt missing, unverified or profile/assets changed')

    def score(self, name, image):
        stage = self.data['stages'][name]
        threshold = stage['threshold']
        if not finite(threshold) or not 0 < threshold <= 0.2:
            raise SafetyStop('Unsafe template threshold')
        templates = self.templates.get(name, [])
        if not templates:
            raise SafetyStop(f'Missing language template: {name}')
        score = min(template_score(image, stage['box'], t, stage.get('vertical', 0)) for t in templates)
        return score, score < threshold
