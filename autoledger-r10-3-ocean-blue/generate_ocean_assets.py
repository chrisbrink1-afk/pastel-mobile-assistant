from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

DARK = '#064A7A'
PRIMARY = '#0875C9'
ACCENT = '#1EA4F2'


def font(size, bold=False):
    candidates = [
        Path(r'C:\Windows\Fonts\segoeuib.ttf' if bold else r'C:\Windows\Fonts\segoeui.ttf'),
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
    ]
    for p in candidates:
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def icon_image(size=256):
    scale = size / 256
    im = Image.new('RGBA', (size, size), (0,0,0,0))
    px = im.load()
    for y in range(size):
        for x in range(size):
            t = (x/size*0.35 + y/size*0.65)
            r1,g1,b1 = (6,45,92); r2,g2,b2 = (0,170,224)
            glow = max(0.0, (t-0.45)/0.55)
            px[x,y] = (int(r1+(r2-r1)*glow), int(g1+(g2-g1)*glow), int(b1+(b2-b1)*glow), 255)
    mask = Image.new('L',(size,size),0)
    ImageDraw.Draw(mask).rounded_rectangle((2,2,size-3,size-3), radius=int(46*scale), fill=255)
    im.putalpha(mask)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((3,3,size-4,size-4), radius=int(44*scale), outline=(70,175,255,255), width=max(2,int(2*scale)))
    shadow = Image.new('RGBA',(size,size),(0,0,0,0)); sd=ImageDraw.Draw(shadow)
    sd.rounded_rectangle((48*scale,92*scale,208*scale,197*scale), radius=int(10*scale), fill=(0,0,0,110))
    shadow=shadow.filter(ImageFilter.GaussianBlur(max(1,int(6*scale)))); im.alpha_composite(shadow)
    d=ImageDraw.Draw(im)
    d.polygon([(47*scale,82*scale),(85*scale,75*scale),(126*scale,90*scale),(126*scale,192*scale),(88*scale,177*scale),(47*scale,181*scale)], fill=(250,252,255,255))
    d.polygon([(130*scale,90*scale),(169*scale,75*scale),(209*scale,82*scale),(209*scale,181*scale),(168*scale,177*scale),(130*scale,192*scale)], fill=(245,248,252,255))
    d.line([(126*scale,90*scale),(126*scale,192*scale)], fill=(210,220,232,255), width=max(1,int(2*scale)))
    for yy in (111,132,153):
        d.rounded_rectangle((155*scale,yy*scale,193*scale,(yy+5)*scale), radius=max(1,int(2*scale)), fill=(6,52,104,255))
    d.polygon([(177*scale,37*scale),(153*scale,78*scale),(173*scale,78*scale),(158*scale,112*scale),(201*scale,65*scale),(180*scale,65*scale)], fill=(50,220,255,255))
    return im


def main():
    root = Path(__file__).resolve().parent / 'assets'
    root.mkdir(parents=True, exist_ok=True)
    icon = icon_image(256)
    icon.save(root/'AUTOLEDGER_ICON.png')
    icon.save(root/'AUTOLEDGER_ICON.ico', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])

    logo = Image.new('RGBA',(480,108),(255,255,255,0))
    small = icon.resize((88,88), Image.Resampling.LANCZOS)
    logo.alpha_composite(small,(8,10))
    d=ImageDraw.Draw(logo)
    f=font(46, True)
    d.text((110,24),'Auto',font=f,fill=(18,42,65,255))
    auto_w=d.textbbox((110,24),'Auto',font=f)[2]-110
    d.text((110+auto_w,24),'Ledger',font=f,fill=(8,117,201,255))
    bbox=logo.getbbox(); logo=logo.crop(bbox)
    logo.save(root/'AUTOLEDGER_LOGO_MODERN.png')
    print('Generated Ocean Blue AUTOLEDGER assets in', root)

if __name__ == '__main__':
    main()
