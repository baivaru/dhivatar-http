import base64
import hashlib
import json
import os
import time
from configparser import ConfigParser
from datetime import datetime

from PIL import ImageColor
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse, FileResponse

from dhivatars import Avatar

# Environment Variables
config_file = "env.ini"
config = ConfigParser()
config.read(config_file)

project_name = config.get('project', 'project_name')
version = config.get('project', 'version', fallback='0.0.1')
github = config.get('project', 'github')
domain = config.get('project', 'fqdn', fallback=None)
cache = config.get('project', 'cache', fallback=False)

# Define allowed cache sizes.
allowed_caches = [64, 150, 200]

# Define folders that are required for the app
folders = ['caches', 'tmp']

# Create required folders if they do not exist
for path in folders:
    if not os.path.exists(path):
        os.makedirs(path)

# Create cache folders if they don't exist
for cache_size in allowed_caches:
    if not os.path.exists(f'caches/{cache_size}'):
        os.makedirs(f'caches/{cache_size}')

# FastAPI instance
app = FastAPI(
    title=project_name, description="A FastAPI for Dhivehi Avatars"
)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# Allow all origins CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """
    Middleware to include response processing time.
    """
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.middleware("http")
async def add_access_control_headers(request: Request, call_next):
    """
    Middleware to try to force client-side caching
    """
    response = await call_next(request)
    response.headers["access-control-max-age"] = str(3600)
    response.headers["cache-control"] = 'max-age=1814400'
    return response


# @app.middleware("http")
# async def print_headers(request: Request, call_next):
#     """
#     Middleware to try to force client-side caching
#     """
#     response = await call_next(request)
#
#     if request.url == deploy_url(''):
#         print(request.headers)
#
#     return response


def deploy_url(url):
    """
    Construct urls for the correct domain during deployment.
    """
    return f"{domain}/{url}" if domain else f"http://localhost:8000/{url}"


async def get_hits_per_day(date_key):
    with open('hits.json', 'r') as f:
        data: dict = json.loads(f.read())
        if date_key in data:
            return data[date_key]
        else:
            return 0


async def store_hits_per_day():
    with open('hits.json', 'r') as f:
        data: dict = json.loads(f.read())
        key = f"{datetime.now().year}-{datetime.now().month}-{datetime.now().day}"
        if key in data:
            data[key] = data[key] + 1
        else:
            data[key] = 1

        with open('hits.json', 'w') as wf:
            wf.write(json.dumps(data))


async def get_chart_data():
    with open('hits.json', 'r') as f:
        data = json.loads(f.read())
        data_keys = sorted(data)
        latest_10 = data_keys[-10:]

        data_10 = []
        for x in latest_10:
            data_10.append(str(data[x]))

        print(latest_10)

        return latest_10, data_10


@app.get('/', response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request):
    date_key = f"{datetime.now().year}-{datetime.now().month}-{datetime.now().day}"

    chart_categories, chart_data = await get_chart_data()

    return templates.TemplateResponse("index.html", {
        "request": request,
        'version': version,
        'docs': deploy_url('docs'),
        'project': github,
        'year': datetime.now().year,
        'hits_per_day': await get_hits_per_day(date_key),
        'chart_data': chart_data,
        'chart_categories': chart_categories
    })


@app.get("/api/")
async def avatar(name: str, size: int = 64, background: str = None, color: str = None):
    """
    Generate your image using your name and other attributes here.

    Size: Up to 1000, any more and you get defaulted to 64.

    Colors: Should be in hex codes, but without the #.
    """
    task = BackgroundTask(store_hits_per_day)

    image = get_image(name, size, background, color)
    if type(image) is str:
        return FileResponse(image, media_type='image/png', background=task)
    else:
        return StreamingResponse(image, media_type='image/png', background=task)


@app.get("/raw/")
async def raw(name: str, size: int = 64, background: str = None, color: str = None):
    """
    Generate your image using your name and other attributes here.

    Size: Up to 1000, any more and you get defaulted to 64.

    Colors: Should be in hex codes, but without the #.

    You will receive a base64 encode of the image, that is ready to be used in any HTML img tag.
    """
    image = get_image(name, size, background, color)

    await store_hits_per_day()

    if type(image) is str:
        return get_base_64(image)
    else:
        return await raw(name, size, background, color)


def get_image(name: str, size: int = 64, background: str = None, color: str = None):
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


def hex_to_rgb(h):
    """
    Convert hexadecimal color to RGB
    """
    if h is not None:
        return ImageColor.getrgb(f"#{h}")
    else:
        return None


def generate_hash(name: str):
    """
    Generate md5 hash of the incoming request name.
    """
    return hashlib.md5(name.encode('utf-8')).hexdigest()


def save_file(bytes_file, filename):
    """
    Save the file
    """
    with open(filename, 'wb+') as f:
        f.write(bytes_file.getbuffer())


def get_base_64(filename):
    """
    Exactly the thing you put in your img src tag
    """
    with open(filename, 'rb') as f:
        data = base64.b64encode(f.read())
        return 'data:image/png;base64,' + data.decode()
