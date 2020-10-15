from configparser import ConfigParser

from PIL import ImageColor
from fastapi import FastAPI
from starlette.responses import StreamingResponse

from dhivatars import Avatar

# Read from config file
config_file = "env.ini"
config = ConfigParser()
config.read(config_file)

project_name = config.get('project', 'project_name')
version = config.get('project', 'version', fallback='0.0.1')
github = config.get('project', 'github')
domain = config.get('project', 'fqdn', fallback=None)

# FastAPI instance
app = FastAPI()


def deploy_url(url):
    """
    Construct urls for the correct domain when deploying.
    :param url:
    :return: str
    """
    return f"{domain}/{url}" if domain else f"http://localhost:8000/{url}"


@app.get('/')
async def home():
    return {
        'app': project_name,
        'description': 'Generate user avatar placeholders that are unique to the user\'s name, but in Dhivehi!',
        'version': version,
        'project': github,
        'docs': deploy_url('docs'),
        'examples': [
            {
                'all_features': deploy_url('api/?name=%DE%84%DE%A6%DE%87%DE%A8%DE%88%DE%A6%DE%83'
                                           '%DE%AA&size=300&background=7e6b5c&color=872361'),
                'size': deploy_url('api/?name=%DE%84%DE%A6%DE%87%DE%A8%DE%88%DE%A6%DE%83%DE%AA'
                                   '&size=300'),
                'background_color': deploy_url('api/?name=%DE%84%DE%A6%DE%87%DE%A8%DE%88%DE%A6%DE%83'
                                               '%DE%AA&background=7e6b5c'),
                'text_color': deploy_url('api/?name=%DE%84%DE%A6%DE%87%DE%A8%DE%88%DE%A6%DE%83'
                                         '%DE%AA&color=872361'),
                'multiple_names': deploy_url('api/?name=%DE%87%DE%A6%DE%80%DE%AA%DE%89%DE%A6%DE%8B%DE%AA%20%DE%89%DE'
                                             '%AA%DE%80%DE%A6%DE%87%DE%B0%DE%89%DE%A6%DE%8B%DE%AA&size=300')
            }
        ]
    }


def hex_to_rgb(h):
    if h is not None:
        return ImageColor.getrgb(f"#{h}")
    else:
        return None


@app.get("/api/")
async def do_the_thing(name: str, size: int = 150, background: str = None, color: str = None):
    if size <= 1000:
        image = Avatar().generate(name, size=size, bg_color=hex_to_rgb(background), font_color=hex_to_rgb(color))
    else:
        image = Avatar().generate(name, bg_color=hex_to_rgb(background), font_color=hex_to_rgb(color))

    return StreamingResponse(image, media_type='image/png')
