"""Render a looping GIF from the latest generated GitHub contribution SVG."""
from copy import deepcopy
from pathlib import Path
import argparse
import math
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFilter

SVG = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG)
T = lambda name: f'{{{SVG}}}{name}'
GOLD = '#F3B552'
BLUE = '#387FC8'
CREAM = '#FAF9F5'


def child(parent, name, attrs=None):
    return ET.SubElement(parent, T(name), attrs or {})


def cell_xy(group):
    match = re.search(r'translate\(\s*([\d.-]+)[ ,]+([\d.-]+)\s*\)', group.get('transform', ''))
    return (float(match.group(1)), float(match.group(2))) if match else (0.0, 0.0)


def decorate(svg_bytes, frame, frame_count):
    root = ET.fromstring(svg_bytes)
    # Set the generator's one-time intro animations to their final values before rasterizing.
    for parent in root.iter():
        for animation in list(parent):
            if animation.tag not in (T('animate'), T('animateTransform')):
                continue
            values = animation.get('values', '').split(';')
            final = values[-1].strip() if values else ''
            if animation.tag == T('animateTransform'):
                kind = animation.get('type', 'translate')
                if kind == 'translate' and final:
                    parent.set('transform', f'translate({final.replace(",", " ")})')
                elif kind == 'rotate' and final:
                    parent.set('transform', f'rotate({final})')
                elif final:
                    parent.set('transform', f'{kind}({final})')
            elif animation.get('attributeName') and final:
                parent.set(animation.get('attributeName'), final)
            parent.remove(animation)
    # Top faces are cloned with a soft gold wash. The source SVG itself is untouched.
    faces = []
    for parent in root.iter():
        for el in list(parent):
            if el.tag == T('rect') and el.get('class', '').startswith('cont-top-'):
                x, y = cell_xy(parent)
                faces.append((parent, el, x + y))
    if not faces:
        raise RuntimeError('Could not find the heatmap blocks in the generated SVG.')
    low = min(item[2] for item in faces)
    span = max(1.0, max(item[2] for item in faces) - low)
    progress = frame / frame_count
    center = low + progress * span
    sigma = span * .085
    for parent, original, position in faces:
        strength = .52 * math.exp(-.5 * ((position - center) / sigma) ** 2)
        if strength < .035:
            continue
        overlay = deepcopy(original)
        overlay.attrib.pop('class', None)
        overlay.set('fill', GOLD)
        overlay.set('fill-opacity', f'{strength:.3f}')
        overlay.set('stroke', CREAM)
        overlay.set('stroke-width', '1.1')
        parent.append(overlay)

    # Radar scanner: a rotating, translucent sector over the existing real values.
    angle = 360 * progress
    radar_parent = next((p for p in root.iter() if any(c.get('class') == 'radar' for c in p)), None)
    if radar_parent is not None:
        sweep = child(radar_parent, 'g', {'transform': f'rotate({angle:.1f})'})
        child(sweep, 'path', {'d': 'M0 0 L0 -142 A142 142 0 0 1 81.5 -116.3 Z',
                              'fill': GOLD, 'fill-opacity': '.15'})
        child(sweep, 'line', {'x1': '0', 'y1': '0', 'x2': '0', 'y2': '-142',
                              'stroke': GOLD, 'stroke-width': '2.2', 'opacity': '.9'})
        child(sweep, 'circle', {'cx': '0', 'cy': '-142', 'r': '3.4', 'fill': GOLD})

    # Orbit around the language donut, matching the profile's blue/gold palette.
    orbit = child(root, 'g', {'transform': f'translate(170 650) rotate({angle:.1f})'})
    child(orbit, 'circle', {'cx': '0', 'cy': '0', 'r': '126', 'fill': 'none',
                            'stroke': '#E4EEF8', 'stroke-width': '3'})
    child(orbit, 'circle', {'cx': '0', 'cy': '0', 'r': '126', 'fill': 'none',
                            'stroke': GOLD, 'stroke-width': '3', 'stroke-dasharray': '88 704'})
    child(orbit, 'circle', {'cx': '126', 'cy': '0', 'r': '5.5', 'fill': BLUE,
                            'stroke': CREAM, 'stroke-width': '2'})
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def rasterize(svg_bytes, output_png, width, renderer):
    if renderer == 'inkscape':
        with tempfile.NamedTemporaryFile(suffix='.svg') as source:
            source.write(svg_bytes)
            source.flush()
            subprocess.run(['inkscape', source.name, f'--export-filename={output_png}',
                            f'--export-width={width}'], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        import cairosvg
        cairosvg.svg2png(bytestring=svg_bytes, write_to=str(output_png), output_width=width)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='profile-3d-contrib/profile-ayush.svg')
    parser.add_argument('--output', default='profile-3d-contrib/profile-ayush.gif')
    parser.add_argument('--renderer', choices=['cairosvg', 'inkscape'], default='cairosvg')
    parser.add_argument('--width', type=int, default=1280)
    parser.add_argument('--frames', type=int, default=30)
    args = parser.parse_args()
    source = Path(args.input)
    if not source.exists():
        raise FileNotFoundError(f'Generated heatmap not found: {source}')
    svg_bytes = source.read_bytes()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    frames = []
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(args.frames):
            png = Path(tmp) / f'{i:03}.png'
            rasterize(decorate(svg_bytes, i, args.frames), png, args.width, args.renderer)
            frames.append(Image.open(png).convert('RGB'))
    # One shared full palette keeps text and thin chart lines crisp between frames.
    sample_height = max(1, int(args.width * 850 / 1280))
    sample = Image.new('RGB', (args.width * 4, sample_height))
    for slot, index in enumerate(sorted(set([0, args.frames // 4, args.frames // 2, 3 * args.frames // 4]))):
        sample.paste(frames[index].resize((args.width, sample_height)), (slot * args.width, 0))
    palette = sample.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    indexed[0].save(output, save_all=True, append_images=indexed[1:], duration=110,
                    loop=0, optimize=True, disposal=1)
    print(f'Wrote {output} ({output.stat().st_size:,} bytes, {args.frames} frames)')


if __name__ == '__main__':
    main()
