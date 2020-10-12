from PIL import ImageColor
from fastapi import FastAPI
from starlette.responses import StreamingResponse

from dhivatars import Avatar

app = FastAPI()


@app.get('/')
def home():
    return {
        'app': 'Dhivatars',
        'description': 'Generate user avatar placeholders, but in Dhivehi!',
        'version': '0.0.1',
        'project': 'https://github.com/baivaru/dhivatar-http',
        'docs': 'https://dhivatars.baivaru.net/docs',
        'examples': [
            'https://dhivatars.baivaru.net/api/?name=%DE%84%DE%A6%DE%87%DE%A8%DE%88%DE%A6%DE%83%DE%AA&size=300'
            '&background=7e6b5c&color=872361',
        ]
    }


def hex_to_rgb(h):
    if h is not None:
        print(ImageColor.getrgb(f"#{h}"))
        return ImageColor.getrgb(f"#{h}")
    else:
        return None


@app.get("/api/")
def do_the_thing(name: str, size: int = 150, background: str = None, color: str = None):
    if size <= 1000:
        image = Avatar().generate(name, size=size, bg_color=hex_to_rgb(background), font_color=hex_to_rgb(color))
    else:
        image = Avatar().generate(name, bg_color=hex_to_rgb(background), font_color=hex_to_rgb(color))

    return StreamingResponse(image, media_type='image/png')
