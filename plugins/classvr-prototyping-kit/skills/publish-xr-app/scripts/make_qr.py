#!/usr/bin/env python3
"""Render the ClassVR QR code for a playlist as a PNG.

    python3 make_qr.py --category-id 1035190927 --title "XR Prototypes" --out qr.png

The headset's built-in scanner understands `AV:CT:<categoryId>` — it selects
that playlist on the device. The QR only depends on the category id, so it is
stable across every rebuild and re-publish; generate it once and keep it.

Prints JSON: {ok, payload, out}
"""
import argparse, json, os, sys

def ensure(mod, pkg):
    try:
        return __import__(mod)
    except ImportError:
        os.system(f'{sys.executable} -m pip install {pkg} --break-system-packages -q >/dev/null 2>&1')
        return __import__(mod)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--category-id', required=True, type=int)
    ap.add_argument('--title', default='XR Prototypes')
    ap.add_argument('--subtitle', default='Scan with the ClassVR headset scanner')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    qrcode = ensure('qrcode', 'qrcode')
    ensure('PIL', 'pillow')
    from PIL import Image, ImageDraw, ImageFont
    from qrcode.constants import ERROR_CORRECT_M

    payload = f'AV:CT:{a.category_id}'
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=16, border=4)
    qr.add_data(payload); qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white').convert('RGB')

    W = max(900, img.width + 200)
    canvas = Image.new('RGB', (W, img.height + 170), 'white')
    canvas.paste(img, ((W - img.width) // 2, 20))
    d = ImageDraw.Draw(canvas)

    def font(sz, bold=False):
        for p in (['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'] if bold else []) + \
                 ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
            try: return ImageFont.truetype(p, sz)
            except Exception: pass
        return ImageFont.load_default()
    def centre(text, y, f, fill='black'):
        w = d.textbbox((0, 0), text, font=f)[2]
        d.text(((W - w) // 2, y), text, font=f, fill=fill)

    y = img.height + 30
    centre(a.title, y, font(34, True))
    centre(a.subtitle, y + 48, font(24), '#555555')
    centre(payload, y + 86, font(20), '#999999')
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or '.', exist_ok=True)
    canvas.save(a.out)

    # confirm the image really decodes to the payload, when a decoder is available
    decoded = None
    try:
        cv2 = __import__('cv2')
        decoded, _, _ = cv2.QRCodeDetector().detectAndDecode(cv2.imread(a.out))
    except Exception:
        pass
    print(json.dumps({'ok': True, 'payload': payload, 'out': os.path.abspath(a.out),
                      'decoded': decoded if decoded else 'not verified (no decoder installed)'}, indent=2))
    return 0

if __name__ == '__main__':
    sys.exit(main())
