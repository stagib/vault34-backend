import asyncio
import aiohttp
import torch
import clip
from PIL import Image
from io import BytesIO

device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)


async def fetch_image(session, post):
    try:
        async with session.get(post.get("file_url"), timeout=30) as res:
            if res.status == 200:
                img_data = await res.read()
                return {
                    "img": Image.open(BytesIO(img_data)).convert("RGB"),
                    "id": post.get("id"),
                }
    except Exception as e:
        return None
    return None


async def fetch_all_images(post_data):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_image(session, post) for post in post_data]
        images = await asyncio.gather(*tasks)
        map = {}
        for image in images:
            if image is None or not image.get("img"):
                continue
            map[image.get("id")] = image.get("img")
        return map


def get_image_vector(image):
    try:
        input = preprocess(image).unsqueeze(0).to(device)
        with torch.no_grad():
            vector = model.encode_image(input).cpu().numpy().tolist()[0]
            return vector
    except Exception as e:
        return None
