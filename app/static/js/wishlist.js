
/* =========================================================
   MARKETLANE - COMPLETE WISHLIST FUNCTIONALITY

   Features:
   1. Load saved wishlist products from the database.
   2. Add and remove products using heart buttons.
   3. Display filled red hearts for saved products.
   4. Update the wishlist count.
   5. Display saved products on wishlist.html.
   6. Remove products from the wishlist page.
   7. Add wishlist products to the shopping cart.
   8. Preserve wishlist data after page refresh.
   ========================================================= */

(() => {
    "use strict";

    // -----------------------------------------------------
    // 1. Identify the current page
    // -----------------------------------------------------

    const wishlistPage = document.querySelector(".wishlist-main");

    const wishlistCount = document.getElementById("wishlist-count");

    const wishlistGrid = document.getElementById("wishlist-items");

    const wishlistLoading = document.getElementById("wishlist-loading");

    const wishlistEmpty = document.getElementById("wishlist-empty");

    const wishlistContent = document.getElementById("wishlist-content");

    const wishlistRetry = document.getElementById("wishlist-retry");

    const wishlistItemLabel = document.getElementById("wishlist-item-label");

    const wishlistMessage = document.getElementById("wishlist-message");


    // -----------------------------------------------------
    // 2. Wishlist state
    // -----------------------------------------------------

    let wishlistProducts = new Set();

    let csrfToken = "";

    const pendingProducts = new Set();


    // -----------------------------------------------------
    // 3. Helper functions
    // -----------------------------------------------------

    function money(paise) {

        return new Intl.NumberFormat("en-IN", {
            style: "currency",
            currency: "INR"
        }).format(paise / 100);
    }


    function createElement(tag, className = "", text = "") {

        const element = document.createElement(tag);

        if (className) {
            element.className = className;
        }

        if (text !== undefined && text !== null) {
            element.textContent = text;
        }

        return element;
    }


    function showMessage(message, error = false) {

        if (wishlistMessage) {

            wishlistMessage.textContent = message;

            wishlistMessage.hidden = false;

            wishlistMessage.classList.toggle("error", error);

        } else {

            const toast = document.getElementById("toast");

            if (toast) {

                toast.textContent = message;

                toast.hidden = false;

                window.setTimeout(() => {
                    toast.hidden = true;
                }, 3500);
            }
        }
    }


    // -----------------------------------------------------
    // 4. Update wishlist count
    // -----------------------------------------------------

    function updateWishlistCount(count = wishlistProducts.size) {

        if (wishlistCount) {
            wishlistCount.textContent = count;
        }
    }


    // -----------------------------------------------------
    // 5. Update all product heart buttons
    // -----------------------------------------------------

    
function updateHeartButtons() {

    document.querySelectorAll(".wishlist-heart").forEach(button => {

        const productId = button.dataset.productId;

        const isWishlisted = wishlistProducts.has(productId);

        button.classList.toggle(
            "is-wishlisted",
            isWishlisted
        );

        button.setAttribute(
            "aria-pressed",
            String(isWishlisted)
        );

        button.setAttribute(
            "aria-label",
            isWishlisted
                ? "Remove from wishlist"
                : "Add to wishlist"
        );

        button.title = isWishlisted
            ? "Remove from wishlist"
            : "Add to wishlist";

        const heart = button.querySelector("span");

        const expectedHeart = isWishlisted ? "♥" : "♡";

        // Change the HTML only if the heart actually needs updating.
        if (heart && heart.textContent !== expectedHeart) {
            heart.textContent = expectedHeart;
        }

        button.disabled = pendingProducts.has(productId);
    });
}


    // -----------------------------------------------------
    // 6. Get CSRF token from cart API
    // -----------------------------------------------------

    async function loadCsrfToken() {

        const response = await fetch("/api/cart", {
            method: "GET",
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error("Could not load session information.");
        }

        const data = await response.json();

        csrfToken = data.csrf_token || "";

        if (!csrfToken) {
            throw new Error("Security token is missing. Reload the page.");
        }
    }


    // -----------------------------------------------------
    // 7. Get saved wishlist products from database
    // -----------------------------------------------------

    async function loadWishlist() {

        const response = await fetch("/api/wishlist", {
            method: "GET",
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error("Could not load your wishlist.");
        }

        const data = await response.json();

        if (!data.success || !Array.isArray(data.products)) {
            throw new Error("Invalid wishlist response.");
        }

        wishlistProducts = new Set(
            data.products.map(product => String(product.id))
        );

        updateWishlistCount(data.count);

        updateHeartButtons();

        // Render products if this is the wishlist page.
        if (wishlistPage) {
            renderWishlist(data.products);
        }
    }


    // -----------------------------------------------------
    // 8. Render products on wishlist.html
    // -----------------------------------------------------

    function renderWishlist(products) {

        wishlistLoading.hidden = true;

        wishlistRetry.hidden = true;

        wishlistEmpty.hidden = products.length !== 0;

        wishlistContent.hidden = products.length === 0;

        wishlistItemLabel.textContent =
            `${products.length} saved ${products.length === 1 ? "product" : "products"}`;

        wishlistGrid.replaceChildren();


        // Create one card for every saved product.
        products.forEach(product => {

            const productId = String(product.id);

            // Main product card.
            const card = createElement("article", "wishlist-card");


            // Product image.
            const image = document.createElement("img");

            image.className = "wishlist-card-image";

            image.alt = product.name;

            image.loading = "lazy";

            image.src = product.image_path
                ? "/static/" + product.image_path
                : "/static/images/placeholder.png";

            image.addEventListener("error", () => {

                image.onerror = null;

                image.src = "/static/images/placeholder.png";

            });


            // Product information.
            const name = createElement("h3", "", product.name);

            const price = createElement(
                "p",
                "wishlist-card-price",
                money(product.price_paise)
            );

            card.append(image, name, price);


            // Optional brand and colour.
            if (product.brand) {

                card.append(
                    createElement("p", "", "Brand: " + product.brand)
                );
            }

            if (product.colour) {

                card.append(
                    createElement("p", "", "Colour: " + product.colour)
                );
            }


            // Stock availability.
            const inStock = Number(product.stock) > 0;

            const stock = createElement(
                "p",
                inStock
                    ? "wishlist-card-stock"
                    : "wishlist-card-stock out-of-stock",
                inStock
                    ? `${product.stock} available`
                    : "Out of stock"
            );

            card.append(stock);


            // Product action buttons.
            const actions = createElement(
                "div",
                "wishlist-card-actions"
            );


            // Add to Cart button.
            const addButton = createElement(
                "button",
                "wishlist-add-cart",
                "Add to Cart"
            );

            addButton.type = "button";

            addButton.dataset.cartAction = "add";

            addButton.dataset.productId = productId;

            addButton.disabled = !inStock;

            if (!inStock) {
                addButton.textContent = "Out of stock";
            }


            // Remove from Wishlist button.
            const removeButton = createElement(
                "button",
                "wishlist-remove",
                "Remove"
            );

            removeButton.type = "button";

            removeButton.dataset.wishlistAction = "remove";

            removeButton.dataset.productId = productId;

            removeButton.setAttribute(
                "aria-label",
                `Remove ${product.name} from wishlist`
            );


            actions.append(addButton, removeButton);

            card.append(actions);

            wishlistGrid.append(card);
        });
    }


    // -----------------------------------------------------
    // 9. Add or remove a product from wishlist
    // -----------------------------------------------------

    async function updateWishlist(action, productId) {

        productId = String(productId || "");

        if (!productId || pendingProducts.has(productId)) {
            return;
        }

        if (!["add", "remove"].includes(action)) {
            return;
        }

        pendingProducts.add(productId);

        updateHeartButtons();

        try {

            const body = new URLSearchParams();

            body.append("action", action);

            body.append("product_id", productId);

            body.append("csrf_token", csrfToken);


            const response = await fetch("/api/wishlist", {

                method: "POST",

                headers: {
                    "Content-Type": "application/x-www-form-urlencoded"
                },

                body: body.toString()

            });


            const data = await response.json();

            if (!response.ok || !data.success) {

                throw new Error(
                    data.error || "Could not update your wishlist."
                );
            }


            // Update local state.
            if (action === "add") {

                wishlistProducts.add(productId);

            } else {

                wishlistProducts.delete(productId);

            }


            updateWishlistCount(data.count);

            updateHeartButtons();


            // Reload the wishlist page products after removal.
            if (wishlistPage) {
                await loadWishlist();
            }


            showMessage(data.message || "Wishlist updated.");

        } catch (error) {

            console.error("Wishlist update error:", error);

            showMessage(error.message, true);

        } finally {

            pendingProducts.delete(productId);

            updateHeartButtons();
        }
    }


    // -----------------------------------------------------
    // 10. Handle heart and remove button clicks
    // -----------------------------------------------------

    document.addEventListener("click", event => {

        const heartButton = event.target.closest(".wishlist-heart");

        const removeButton = event.target.closest(
            '[data-wishlist-action="remove"]'
        );


        // Heart button on catalog page.
        if (heartButton) {

            if (heartButton.disabled) {
                return;
            }

            const productId = heartButton.dataset.productId;

            const action = wishlistProducts.has(productId)
                ? "remove"
                : "add";

            updateWishlist(action, productId);

            return;
        }


        // Remove button on wishlist page.
        if (removeButton) {

            if (removeButton.disabled) {
                return;
            }

            updateWishlist(
                "remove",
                removeButton.dataset.productId
            );
        }
    });


    // -----------------------------------------------------
    // 11. Retry loading wishlist
    // -----------------------------------------------------

    if (wishlistRetry) {

        wishlistRetry.addEventListener("click", initializeWishlist);
    }


    // -----------------------------------------------------
    // 12. Watch dynamically loaded catalog products
    // -----------------------------------------------------

    
const productGrid = document.querySelector(".product-grid");

if (productGrid) {

    const observer = new MutationObserver(() => {

        // Synchronize only when new product cards are added.
        // Avoid repeatedly updating unchanged heart icons.

        updateHeartButtons();

    });

    observer.observe(productGrid, {
        childList: true,
        subtree: true
    });
}


    // -----------------------------------------------------
    // 13. Initialize wishlist
    // -----------------------------------------------------

    async function initializeWishlist() {

        if (wishlistLoading) {
            wishlistLoading.hidden = false;
        }

        if (wishlistRetry) {
            wishlistRetry.hidden = true;
        }

        try {

            await loadCsrfToken();

            await loadWishlist();

        } catch (error) {

            console.error("Wishlist loading error:", error);

            if (wishlistLoading) {
                wishlistLoading.hidden = true;
            }

            if (wishlistRetry) {
                wishlistRetry.hidden = false;
            }

            showMessage(error.message, true);
        }
    }


    // Start the wishlist functionality.
    initializeWishlist();

})();
