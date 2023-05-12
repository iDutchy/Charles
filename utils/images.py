import struct

from PIL import Image
from io import BytesIO

def changePNGColor(sourceFile, fromRgb, toRgb, deltaRank = 10):
    fromRgb = fromRgb.replace('#', '').replace('0x', '')
    toRgb = toRgb.replace('#', '').replace('0x', '')

    fromColor = struct.unpack('BBB', bytes.fromhex(fromRgb))
    toColor = struct.unpack('BBB', bytes.fromhex(toRgb))

    img = Image.open(sourceFile)
    img = img.convert("RGBA")
    pixdata = img.load()

    for x in range(0, img.size[0]):
        for y in range(0, img.size[1]):
            rdelta = pixdata[x, y][0] - fromColor[0]
            gdelta = pixdata[x, y][0] - fromColor[0]
            bdelta = pixdata[x, y][0] - fromColor[0]
            if abs(rdelta) <= deltaRank and abs(gdelta) <= deltaRank and abs(bdelta) <= deltaRank:
                pixdata[x, y] = (toColor[0] + rdelta, toColor[1] + gdelta, toColor[2] + bdelta, pixdata[x, y][3])

    buf = BytesIO()
    img.save(buf, "png")
    buf.seek(0)

    return buf


async def make_transparent(bot, image, color=None, *, treshold: int=0):
    col = color or (255, 255, 255)
    async with bot.session.get(image) as f:
        img = Image.open(BytesIO(await f.read())).convert("RGBA")

    datas = img.getdata()

    newData = []
    for item in datas:
        if treshold:
            if ((col[0]-treshold) < item[0] < (col[0]+treshold)) and ((col[1]-treshold) < item[1] < (col[1]+treshold)) and ((col[2]-treshold) < item[2] < (col[2]+treshold)):
                newData.append((255, 255, 255, 0))
            else:
                newData.append(item)
        else:
            if (item[0], item[1], item[2]) == col:
                newData.append((255, 255, 255, 0))
            else:
                newData.append(item)

    img.putdata(newData)

    buf = BytesIO()
    img.save(buf, "png")
    buf.seek(0)
    img.close()
    return buf