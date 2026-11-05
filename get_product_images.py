"""
MarketLane product image finder
--------------------------------
1) Searches Openverse for up to 2 openly-licensed image candidates per product.
2) Saves candidates and creates category-wise contact sheets.
3) Creates image_choices.csv for quick review.
4) After editing selected_candidate (0, 1, or 2), run:
       python get_product_images.py --finalize

No API key is required for basic anonymous searches. Search results may not be exact
product-model matches; review the contact sheets before approving them.
"""

import argparse
import csv
import io
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

CSV_FILE = Path("marketlane_100_products.csv")
CANDIDATE_DIR = Path("image_candidates")
OUTPUT_DIR = Path("app/static/images/products")
PLACEHOLDER = Path("app/static/images/placeholder.png")
CHOICES_FILE = Path("image_choices.csv")
API_URL = "https://api.openverse.org/v1/images/"
HEADERS = {"User-Agent": "MarketLaneStudentProject/1.0 (product image research)"}
MAX_CANDIDATES = 2
IMAGE_SIZE = (800, 800)
TIMEOUT = 25


def safe_name(value):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(value)).strip("_")


def read_products():
    if not CSV_FILE.exists():
        raise FileNotFoundError(f"Cannot find {CSV_FILE}. Run this script from your project root.")
    with CSV_FILE.open("r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError("The product CSV is empty.")
    required = {"id", "name", "brand"}
    missing = required - set(rows[0].keys())
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")
    return rows


def download_candidate(product, number, result):
    product_id = safe_name(product["id"])
    folder = CANDIDATE_DIR / product_id
    folder.mkdir(parents=True, exist_ok=True)

    image_url = result.get("url") or result.get("thumbnail")
    if not image_url:
        return None

    try:
        response = requests.get(image_url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content)).convert("RGB")
        if image.width < 120 or image.height < 120:
            return None
        image.thumbnail((1000, 1000))
        path = folder / f"candidate_{number}.jpg"
        image.save(path, "JPEG", quality=90, optimize=True)
        return path
    except Exception as exc:
        print(f"  Could not download candidate {number}: {exc}")
        return None


def search_candidates(products):
    review_rows = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for index, product in enumerate(products, start=1):
        product_id = product["id"].strip()
        brand = product.get("brand", "").strip()
        name = product.get("name", "").strip()
        colour = product.get("colour", "").strip()
        query = " ".join(part for part in [brand, name, colour, "product"] if part)

        print(f"[{index}/{len(products)}] Searching: {product_id} - {query}")
        entry = {
            "id": product_id,
            "name": name,
            "brand": brand,
            "candidate_1": "",
            "candidate_2": "",
            "selected_candidate": "0",
            "source_1": "",
            "license_1": "",
            "creator_1": "",
            "source_2": "",
            "license_2": "",
            "creator_2": "",
        }

        try:
            response = session.get(
                API_URL,
                params={
                    "q": query[:190],
                    "page_size": 8,
                    "license_type": "commercial",
                    "mature": "false",
                },
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            results = response.json().get("results", [])
        except Exception as exc:
            print(f"  Search failed: {exc}")
            results = []

        saved = 0
        for result in results:
            if saved >= MAX_CANDIDATES:
                break
            path = download_candidate(product, saved + 1, result)
            if path is None:
                continue
            saved += 1
            entry[f"candidate_{saved}"] = str(path).replace("\\", "/")
            entry[f"source_{saved}"] = result.get("foreign_landing_url", "")
            entry[f"license_{saved}"] = " ".join(
                str(result.get(k, "")) for k in ("license", "license_version")
            ).strip()
            entry[f"creator_{saved}"] = result.get("creator", "") or ""
        print(f"  Saved {saved} candidate(s).")
        review_rows.append(entry)
        time.sleep(1.1)  # Respect anonymous API rate limits.

    fields = list(review_rows[0].keys())
    with CHOICES_FILE.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(review_rows)

    make_contact_sheets(review_rows)
    print("\nSearch complete.")
    print(f"Review file: {CHOICES_FILE}")
    print(f"Candidate images: {CANDIDATE_DIR}")
    print("Open the contact sheets inside image_candidates/contact_sheets.")
    print("In image_choices.csv, set selected_candidate to 1, 2, or 0 for each product.")
    print("Use 0 if neither candidate is a correct/suitable match.")


def make_contact_sheets(rows):
    sheet_dir = CANDIDATE_DIR / "contact_sheets"
    sheet_dir.mkdir(parents=True, exist_ok=True)
    grouped = {}
    for row in rows:
        product_id = row["id"]
        category = "Other"
        # Recover category from original CSV by matching product ID.
        grouped.setdefault(category, []).append(row)

    # Use one sheet per 20 products to keep text readable.
    for start in range(0, len(rows), 20):
        batch = rows[start:start + 20]
        cols, cell_w, cell_h = 4, 250, 230
        rows_needed = (len(batch) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell_w, rows_needed * cell_h), "white")
        draw = ImageDraw.Draw(sheet)
        for i, item in enumerate(batch):
            x = (i % cols) * cell_w
            y = (i // cols) * cell_h
            draw.rectangle((x, y, x + cell_w - 1, y + cell_h - 1), outline="#bbbbbb")
            draw.text((x + 8, y + 6), f'{item["id"]} | {item["name"][:27]}', fill="black")
            for candidate_no in (1, 2):
                image_path = item.get(f"candidate_{candidate_no}")
                bx = x + 8 + (candidate_no - 1) * 118
                by = y + 34
                if image_path and Path(image_path).exists():
                    try:
                        with Image.open(image_path) as im:
                            thumb = ImageOps.contain(im.convert("RGB"), (108, 145))
                        sheet.paste(thumb, (bx, by))
                        draw.text((bx, by + 148), f"Option {candidate_no}", fill="black")
                    except Exception:
                        draw.text((bx, by + 20), "Unreadable", fill="red")
                else:
                    draw.text((bx, by + 20), f"Option {candidate_no}: none", fill="gray")
        out = sheet_dir / f"contact_sheet_{start // 20 + 1:02d}.jpg"
        sheet.save(out, "JPEG", quality=88)
    print(f"Created {((len(rows) + 19) // 20)} contact sheets.")


def finalize_images(products):
    if not CHOICES_FILE.exists():
        raise FileNotFoundError("Run the search first; image_choices.csv does not exist.")
    with CHOICES_FILE.open("r", newline="", encoding="utf-8-sig") as f:
        choices = {row["id"]: row for row in csv.DictReader(f)}

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    copied = 0
    placeholders = 0
    missing = []

    for product in products:
        product_id = product["id"].strip()
        choice = choices.get(product_id, {})
        selected = str(choice.get("selected_candidate", "0")).strip()
        if selected in ("1", "2"):
            candidate = Path(choice.get(f"candidate_{selected}", ""))
            if candidate.exists():
                try:
                    with Image.open(candidate) as im:
                        im = im.convert("RGB")
                        canvas = Image.new("RGB", IMAGE_SIZE, "white")
                        fitted = ImageOps.contain(im, IMAGE_SIZE)
                        canvas.paste(fitted, ((800 - fitted.width) // 2, (800 - fitted.height) // 2))
                        canvas.save(OUTPUT_DIR / f"{safe_name(product_id)}.jpg",
                                    "JPEG", quality=90, optimize=True)
                    copied += 1
                    continue
                except Exception as exc:
                    print(f"{product_id}: selected image failed ({exc}); using placeholder.")
        if PLACEHOLDER.exists():
            # Product CSV/database can use this shared placeholder path.
            placeholders += 1
        else:
            missing.append(product_id)

    print("\nFinalization complete.")
    print(f"Approved product images saved: {copied}")
    print(f"Products left on placeholder: {placeholders}")
    if missing:
        print("Placeholder file missing; these products need attention:", ", ".join(missing))
    print(f"Output folder: {OUTPUT_DIR}")
    print("Images are named automatically using each product ID.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--finalize", action="store_true",
                        help="Copy reviewed selections into app/static/images/products.")
    args = parser.parse_args()
    products = read_products()
    if args.finalize:
        finalize_images(products)
    else:
        search_candidates(products)


if __name__ == "__main__":
    main()
