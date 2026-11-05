import requests
from pathlib import Path
from PIL import Image
from io import BytesIO

url = (
    "https://images.unsplash.com/photo-1606220945770-b5b6c2c55bf1"
    "?auto=format&fit=crop&w=800&q=85"
)

folder = Path("app/static/images/products")
folder.mkdir(parents=True, exist_ok=True)

response = requests.get(url, timeout=30)
response.raise_for_status()

image = Image.open(BytesIO(response.content)).convert("RGB")
image.save(folder / "test_image.jpg", quality=90)

print("Image downloaded successfully.")
print("Image size:", image.size)
print("Saved at:", folder / "test_image.jpg")