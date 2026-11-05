from run import app
from app.database import get_db

with app.app_context():

    db = get_db()

    print("\n========== SHOPPING CART TABLE STRUCTURE ==========\n")

    columns = db.execute(
        'PRAGMA table_info("shopping_carts")'
    ).fetchall()

    for column in columns:
        print(
            f"Column: {column['name']} | "
            f"Type: {column['type']} | "
            f"Primary Key: {column['pk']}"
        )

    print("\n========== SHOPPING CART RECORDS ==========\n")

    records = db.execute(
        "SELECT * FROM shopping_carts LIMIT 10"
    ).fetchall()

    if records:
        for record in records:
            print(dict(record))
    else:
        print("No shopping cart records found.")