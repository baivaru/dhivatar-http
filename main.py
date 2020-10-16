import base64
import hashlib
import os
import time
from configparser import ConfigParser

from PIL import ImageColor
from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse, FileResponse

from dhivatars import Avatar

# Read from config file
config_file = "env.ini"
config = ConfigParser()
config.read(config_file)

project_name = config.get('project', 'project_name')
version = config.get('project', 'version', fallback='0.0.1')
github = config.get('project', 'github')
domain = config.get('project', 'fqdn', fallback=None)
cache = config.get('project', 'cache', fallback=False)

allowed_caches = [150, 200, 300]

folders = ['caches', 'tmp']
# Create cache folders if they don't exist
for path in folders:
    if not os.path.exists(path):
        os.makedirs(path)

for cache_size in allowed_caches:
    if not os.path.exists(f'caches/{cache_size}'):
        os.makedirs(f'caches/{cache_size}')

# FastAPI instance
app = FastAPI(
    title=project_name, description="A FastAPI for Dhivehi Avatars"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.middleware("http")
async def add_access_control_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["access-control-max-age"] = str(3600)
    response.headers["cache-control"] = 'max-age=1814400'
    return response


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
async def avatar(name: str, size: int = 150, background: str = None, color: str = None):
    image = get_image(name, size, background, color)
    if type(image) is str:
        return FileResponse(image, media_type='image/png')
    else:
        return StreamingResponse(image, media_type='image/png')


@app.get("/raw/")
async def raw(name: str, size: int = 150, background: str = None, color: str = None):
    image = get_image(name, size, background, color)

    if type(image) is str:
        return get_base_64(image)
    else:
        return await raw(name, size, background, color)


def get_image(name: str, size: int = 150, background: str = None, color: str = None):
    if cache and size in allowed_caches and background is None and color is None:
        name_and_size = f"{name}{size}"
        hashed_string = generate_hash(name_and_size)
        file_name = f'caches/{size}/{hashed_string}.png'

        if os.path.exists(file_name):
            return file_name
        else:
            image = Avatar().generate(name, size=size, bg_color=hex_to_rgb(background),
                                      font_color=hex_to_rgb(color))

            save_file(image, file_name)
            return image

    else:
        if size <= 1000:
            image = Avatar().generate(name, size=size, bg_color=hex_to_rgb(background), font_color=hex_to_rgb(color))
        else:
            image = Avatar().generate(name, bg_color=hex_to_rgb(background), font_color=hex_to_rgb(color))

        return image


def generate_hash(name: str):
    """ Generate md5 hash of the incoming request name. """
    return hashlib.md5(name.encode('utf-8')).hexdigest()


def save_file(bytes_file, filename):
    """ Save the file"""
    with open(filename, 'wb+') as f:
        f.write(bytes_file.getbuffer())


def get_base_64(filename):
    """ Exactly the thing you put in your img src tag"""
    with open(filename, 'rb') as f:
        data = base64.b64encode(f.read())
        return 'data:image/png;base64,' + data.decode()
