"""Rotate Ayush's profile colours without progressively recolouring previous outputs.

profile: keep original assets once, generate today's images, update README image URLs.
heatmap: recolour the freshly generated live SVG/GIF after animate_heatmap.py.
Run from repository root. Original assets are kept in profile-themes/source/.
"""
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import argparse
import io
import json
import os
import re
import shutil
from urllib.parse import urlsplit, parse_qsl, urlencode, urlunsplit

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'profile-themes'
SOURCE = DIRECTORY / 'source'
ASSETS = ['01-hero.svg', '02-about.gif', '03-stack.svg', '04-projects.gif',
          '05-experience.gif', '06-connect.gif', 'link-email.svg',
          'link-linkedin.svg', 'link-portfolio.svg']
BASE_HEX = ['#FAF9F5', '#393943', '#387FC8', '#F3B552', '#E4EEF8',
            '#FFFFFF', '#D5D6DA', '#000000']


def rgb(value):
    return np.array([int(value[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)


class Palette:
    def __init__(self, theme):
        self.theme = theme
        self.base = np.array([rgb(h) for h in BASE_HEX])
        self.target = np.array([rgb(theme[k]) for k in ['bg', 'ink', 'primary', 'accent', 'soft']]
                               + [rgb('#FFFFFF'), rgb(theme['soft']), rgb('#000000')])

    def map(self, colours):
        """Map antialiased colours as blends of the closest two source anchors."""
        colours = np.asarray(colours, dtype=float)
        best = np.full(len(colours), float('inf'))
        result = np.zeros((len(colours), 3))
        for i in range(len(self.base)):
            for j in range(i + 1, len(self.base)):
                delta = self.base[j] - self.base[i]
                mix = np.clip(((colours - self.base[i]) * delta).sum(1) / (delta * delta).sum(), 0, 1)
                predicted = self.base[i] + mix[:, None] * delta
                error = ((predicted - colours) ** 2).sum(1)
                take = error < best
                result[take] = self.target[i] + mix[take, None] * (self.target[j] - self.target[i])
                best[take] = error[take]
        return np.uint8(np.clip(result, 0, 255))

    def svg(self, data):
        text = data.decode('utf-8')
        # Only paint hex tokens, never title/content text.
        pattern = r'#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b'
        colours = sorted(set(re.findall(pattern, text)))
        if not colours:
            return data
        expanded = [c if len(c) == 7 else '#' + ''.join(x * 2 for x in c[1:]) for c in colours]
        mapped = self.map([rgb(c) for c in expanded])
        replacements = {c: '#' + ''.join(f'{v:02X}' for v in row) for c, row in zip(colours, mapped)}
        return re.sub(pattern, lambda m: replacements[m[0]], text).encode('utf-8')

    def gif(self, data):
        image = Image.open(io.BytesIO(data))
        frames, durations = [], []
        has_alpha = False
        for index in range(image.n_frames):
            image.seek(index)
            # Pillow composites GIF delta frames before conversion.
            rgba = image.convert('RGBA')
            alpha = np.array(rgba.getchannel('A')) < 128
            has_alpha = has_alpha or bool(alpha.any())
            frame = rgba.convert('RGB').quantize(colors=255, method=Image.Quantize.FASTOCTREE)
            colours = frame.getpalette()
            colours += [0] * (768 - len(colours))
            mapped = self.map(np.array(colours).reshape(256, 3))
            frame.putpalette(mapped.flatten().tolist())
            if alpha.any():
                values = np.array(frame)
                values[alpha] = 255
                frame = Image.fromarray(values).convert('P')
                frame.putpalette(mapped.flatten().tolist())
            frames.append(frame)
            durations.append(image.info.get('duration', 100))
        buffer = io.BytesIO()
        options = dict(save_all=True, append_images=frames[1:], duration=durations,
                       loop=image.info.get('loop', 0), optimize=True, disposal=2 if has_alpha else 1)
        if has_alpha:
            options['transparency'] = 255
        frames[0].save(buffer, format='GIF', **options)
        return buffer.getvalue()

    def file(self, source, output):
        data = source.read_bytes()
        if self.theme['id'] == 'blue-gold':
            result = data  # exact original animation/quality when returning to blue-gold
        else:
            result = self.gif(data) if source.suffix.lower() == '.gif' else self.svg(data)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(result)


def update_readme(theme, day):
    readme = ROOT / 'README.md'
    text = readme.read_text(encoding='utf-8')
    local_paths = set(ASSETS + ['profile-3d-contrib/profile-ayush.gif'])
    version = f"{day}-{theme['id']}"

    def replace(match):
        value = match.group(1)
        parsed = urlsplit(value.replace('&amp;', '&'))
        if parsed.path in local_paths and not parsed.netloc:
            query = dict(parse_qsl(parsed.query))
            query['v'] = version
            updated = urlunsplit(('', '', parsed.path, urlencode(query), parsed.fragment))
            return 'src="' + updated.replace('&', '&amp;') + '"'
        if parsed.netloc == 'img.shields.io':
            # Keep every existing href and label; change only the three project badge paints.
            roles = [('JOBPULSE-', 'primary'), ('COLLEGE%20ADVISOR-', 'accent'), ('NTECH-', 'soft')]
            for marker, role in roles:
                if marker in parsed.path:
                    path = re.sub(r'-[0-9A-Fa-f]{6}$', '-' + theme[role][1:], parsed.path)
                    query = dict(parse_qsl(parsed.query))
                    query['labelColor'] = theme['ink'][1:]
                    query['logoColor'] = theme['bg'][1:]
                    updated = urlunsplit((parsed.scheme, parsed.netloc, path, urlencode(query), parsed.fragment))
                    return 'src="' + updated.replace('&', '&amp;') + '"'
        return match[0]

    text = re.sub(r'src="([^"]+)"', replace, text)
    readme.write_text(text, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['profile', 'heatmap'])
    parser.add_argument('--theme', default='auto')
    parser.add_argument('--date', help='YYYY-MM-DD override for local verification')
    args = parser.parse_args()
    config = json.loads((DIRECTORY / 'themes.json').read_text())
    today = date.fromisoformat(args.date) if args.date else datetime.now(ZoneInfo(config['timezone'])).date()
    state_path = DIRECTORY / 'state.json'
    if args.phase == 'profile':
        state = json.loads(state_path.read_text()) if state_path.exists() else {'start_date': today.isoformat()}
        themes = config['themes']
        available = {t['id']: t for t in themes}
        if args.theme == 'auto':
            offset = (today - date.fromisoformat(state['start_date'])).days
            theme = themes[offset % len(themes)]
        else:
            if args.theme not in available:
                raise ValueError(f'Unknown theme: {args.theme}')
            theme = available[args.theme]
        missing = [p for p in ASSETS if not (ROOT / p).exists()]
        if missing:
            raise FileNotFoundError('Upload these existing profile assets first: ' + ', '.join(missing))
        if SOURCE.exists() and any(not (SOURCE / p).exists() for p in ASSETS):
            raise RuntimeError('Incomplete source backup. Restore profile-themes/source/ from Git history before running.')
        if not SOURCE.exists():
            SOURCE.mkdir(parents=True)
            for name in ASSETS:
                shutil.copyfile(ROOT / name, SOURCE / name)
            print('Saved original profile assets in profile-themes/source/.')
        palette = Palette(theme)
        for name in ASSETS:
            palette.file(SOURCE / name, ROOT / name)
        update_readme(theme, today.isoformat())
        state.update({'date': today.isoformat(), 'theme_id': theme['id'], 'theme_name': theme['name']})
        state_path.write_text(json.dumps(state, indent=2) + '\n')
        print(f"Theme for {today}: {theme['name']}")
        if os.environ.get('GITHUB_STEP_SUMMARY'):
            with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as stream:
                stream.write(f"## Daily profile theme\n{today} · **{theme['name']}**\n")
    else:
        if not state_path.exists():
            raise RuntimeError('Run the profile phase before the heatmap phase.')
        state = json.loads(state_path.read_text())
        theme = next(t for t in config['themes'] if t['id'] == state['theme_id'])
        palette = Palette(theme)
        for suffix in ['svg', 'gif']:
            path = ROOT / 'profile-3d-contrib' / f'profile-ayush.{suffix}'
            if not path.exists():
                raise FileNotFoundError(f'Generate the live heatmap first: {path}')
            palette.file(path, path)
        print('Fresh contribution heatmap matches ' + theme['name'])


if __name__ == '__main__':
    main()
