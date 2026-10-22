from flask import Flask, render_template


def create_app():
    app = Flask(__name__)

    products = {
        "P101": {
            "name": "Wireless Mouse",
            "category": "Electronics",
            "price_paise": 79900,
            "stock": 20,
        },
        "P102": {
            "name": "Mechanical Keyboard",
            "category": "Electronics",
            "price_paise": 249900,
            "stock": 12,
        },
        "P103": {
            "name": "Classic Cotton T-Shirt",
            "category": "Clothing",
            "price_paise": 59900,
            "stock": 18,
        },
        "P104": {
            "name": "Everyday Sneakers",
            "category": "Footwear",
            "price_paise": 179900,
            "stock": 4,
        },
        "P105": {
            "name": "Everyday Backpack",
            "category": "Accessories",
            "price_paise": 149900,
            "stock": 10,
        },
        "P106": {
            "name": "Hardcover Notebook",
            "category": "Stationery",
            "price_paise": 19900,
            "stock": 30,
        },
    }

    @app.route("/")
    def catalog():
        return render_template("catalog.html", products=products)

    return app