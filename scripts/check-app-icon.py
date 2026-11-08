"""Focused icon check: fallback, asset sizes/alpha, local-only art, compiled bundle metadata."""
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import subprocess
import tempfile

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('app_icon', ROOT / 'scripts/prepare-app-icon.py')
icon = importlib.util.module_from_spec(spec); spec.loader.exec_module(icon)


def check_catalog(catalog):
    folder = catalog / 'AppIcon.appiconset'
    rows = json.loads((folder / 'Contents.json').read_text())['images']
    assert len(rows) == 20
    for row in rows:
        size = int(float(row['size'].split('x')[0]) * int(row['scale'][0]))
        image = Image.open(folder / row['filename'])
        assert image.size == (size, size), row
        if row['idiom'] == 'mac':
            assert image.mode == 'RGBA' and image.getpixel((0, 0))[3] < 10
        else:
            assert image.mode == 'RGB', 'iOS icons must be opaque'


def check_bundle(path):
    info_path = path / ('Contents/Info.plist' if (path / 'Contents').exists() else 'Info.plist')
    info = plistlib.loads(info_path.read_bytes())
    resources = path / 'Contents/Resources' if (path / 'Contents').exists() else path
    assert (resources / 'Assets.car').is_file(), path
    if 'CFBundleIcons~ipad' in info:
        primary = info['CFBundleIcons~ipad']['CFBundlePrimaryIcon']
        assert primary['CFBundleIconName'] == 'AppIcon', primary
        assert primary['CFBundleIconFiles'], primary
        assert list(resources.glob('AppIcon*.png')), path
    else:
        assert info.get('CFBundleIconName') == 'AppIcon', info
        filename = resources / info['CFBundleIconFile']
        assert filename.is_file() or filename.with_suffix('.icns').is_file(), info


def main():
    fallback_art = Image.open(ROOT / 'App/IconFallback.png').convert('RGB')
    assert ImageChops.difference(fallback_art, icon.face(None)).getbbox() is None, 'Fallback must contain only the original compass design'
    result = icon.generate()
    check_catalog(icon.CATALOG)
    assert Image.open(ROOT / 'work/icon/preview.png').width > 1800
    tracked = subprocess.check_output(['git', 'ls-files', 'App/GeneratedIcons.xcassets', 'App/GameData'], cwd=ROOT, text=True)
    assert not tracked, 'Retail-derived art must never be tracked'
    subprocess.run(['git', 'check-ignore', '-q', str(icon.CATALOG / 'AppIcon.appiconset/Contents.json')], cwd=ROOT, check=True)
    with tempfile.TemporaryDirectory(dir=ROOT / 'work/icon') as tmp:
        tmp = Path(tmp)
        fallback = icon.generate(data=tmp / 'absent', catalog=tmp / 'Fallback.xcassets', preview=tmp / 'preview.png')
        assert fallback['source'] == 'original compass fallback'
        check_catalog(tmp / 'Fallback.xcassets')
    build = ROOT / os.environ.get('CLAW_DERIVED_DATA', 'work/MacCatalyst') / 'Build/Products'
    checked = []
    for configuration in ('Release-maccatalyst', 'Release-iphoneos'):
        bundle = build / configuration / 'Claw.app'
        check_bundle(bundle)
        checked.append(str(bundle))
    print(json.dumps(dict(status='pass', checks=['retail generation', 'fallback without GameData', '20 valid slots', 'opaque iPad / transparent Mac', 'ignored art', 'compiled icon metadata'], bundles=checked, preview=result['preview'])))


if __name__ == '__main__':
    main()
