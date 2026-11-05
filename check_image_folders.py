from pathlib import Path
from run import app

static_folder = Path(app.static_folder)

folders = [
    static_folder / "images",
    static_folder / "images" / "products",
    static_folder / "uploads",
    static_folder / "uploads" / "products"
]

print("\n========== IMAGE FOLDER CHECK ==========\n")

for folder in folders:

    print(f"\nFolder: {folder}")

    if not folder.exists():
        print("Status: Folder does not exist")
        continue

    files = [
        file for file in folder.rglob("*")
        if file.is_file()
    ]

    print(f"Total files: {len(files)}")

    for file in files[:15]:
        print(f"  - {file.name}")

    if len(files) > 15:
        print(f"  ... and {len(files) - 15} more files")