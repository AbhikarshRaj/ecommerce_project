"use strict";

// ---------- Missing images ----------

document.querySelectorAll("img").forEach((image) => {
    const hideBrokenImage = () => {
        image.hidden = true;
    };

    image.addEventListener("error", hideBrokenImage);

    // Handles images that failed before this script started.
    if (image.complete && image.naturalWidth === 0) {
        hideBrokenImage();
    }
});

// ---------- Search and category filters ----------

const searchInput = document.querySelector("#product-search");
const categoryButtons = document.querySelectorAll(".category-button");
const productCards = [...document.querySelectorAll(".product-card")];
const resultCount = document.querySelector("#result-count");
const emptyState = document.querySelector("#empty-state");

let selectedCategory = "all";

function filterProducts() {
    const query = searchInput.value.trim().toLowerCase();
    let visibleCount = 0;

    productCards.forEach((card) => {
        const matchesCategory =
            selectedCategory === "all" ||
            card.dataset.category === selectedCategory;

        const matchesSearch = card.dataset.name.includes(query);
        const visible = matchesCategory && matchesSearch;

        card.hidden = !visible;

        if (visible) {
            visibleCount += 1;
        }
    });

    resultCount.textContent =
        `${visibleCount} ${visibleCount === 1 ? "product" : "products"}`;

    emptyState.hidden = visibleCount !== 0;
}

function selectCategory(category) {
    selectedCategory = category;

    categoryButtons.forEach((button) => {
        const active = button.dataset.category === category;

        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", String(active));
    });

    filterProducts();
}

function scrollToProducts() {
    document.querySelector("#products").scrollIntoView({
        block: "start"
    });
}

categoryButtons.forEach((button) => {
    button.addEventListener("click", () => {
        selectCategory(button.dataset.category);
        scrollToProducts();
    });
});

searchInput.addEventListener("input", filterProducts);

document.querySelector("#search-form").addEventListener("submit", (event) => {
    event.preventDefault();
    filterProducts();
    scrollToProducts();
});

document.querySelector("#reset-filters").addEventListener("click", () => {
    searchInput.value = "";
    selectCategory("all");
    searchInput.focus();
});

document.querySelectorAll("[data-shop-category]").forEach((button) => {
    button.addEventListener("click", () => {
        searchInput.value = "";
        selectCategory(button.dataset.shopCategory);
        scrollToProducts();
    });
});

// ---------- Banner carousel ----------

const hero = document.querySelector(".hero");
const slides = [...document.querySelectorAll(".slide")];
const dots = [...document.querySelectorAll(".slide-dot")];
const toggleButton = document.querySelector("#toggle-slides");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

let currentSlide = 0;
let timer = null;
let playing = !reducedMotion.matches;
let pointerInside = false;

function showSlide(index) {
    currentSlide = (index + slides.length) % slides.length;

    slides.forEach((slide, slideIndex) => {
        slide.hidden = slideIndex !== currentSlide;
    });

    dots.forEach((dot, dotIndex) => {
        const active = dotIndex === currentSlide;

        dot.classList.toggle("active", active);

        if (active) {
            dot.setAttribute("aria-current", "true");
        } else {
            dot.removeAttribute("aria-current");
        }
    });
}

function stopTimer() {
    window.clearInterval(timer);
    timer = null;
}

function syncPlayback() {
    stopTimer();

    toggleButton.textContent = playing ? "Ⅱ" : "▶";
    toggleButton.setAttribute(
        "aria-label",
        playing ? "Pause slideshow" : "Play slideshow"
    );

    if (playing && !pointerInside && !document.hidden) {
        timer = window.setInterval(() => {
            showSlide(currentSlide + 1);
        }, 5500);
    }
}

document.querySelector("#previous-slide").addEventListener("click", () => {
    showSlide(currentSlide - 1);
    syncPlayback();
});

document.querySelector("#next-slide").addEventListener("click", () => {
    showSlide(currentSlide + 1);
    syncPlayback();
});

dots.forEach((dot) => {
    dot.addEventListener("click", () => {
        showSlide(Number(dot.dataset.slide));
        syncPlayback();
    });
});

toggleButton.addEventListener("click", () => {
    playing = !playing;
    syncPlayback();
});

hero.addEventListener("mouseenter", () => {
    pointerInside = true;
    syncPlayback();
});

hero.addEventListener("mouseleave", () => {
    pointerInside = false;
    syncPlayback();
});

// Stop automatic changes when a keyboard user enters the carousel.
// They can explicitly restart using the Play button.
hero.addEventListener("focusin", () => {
    if (playing) {
        playing = false;
        syncPlayback();
    }
});

document.addEventListener("visibilitychange", syncPlayback);

reducedMotion.addEventListener("change", () => {
    if (reducedMotion.matches) {
        playing = false;
        syncPlayback();
    }
});

showSlide(0);
syncPlayback();

// ---------- Cart placeholder ----------

let toastTimer;

document.querySelector("#cart-button").addEventListener("click", () => {
    const toast = document.querySelector("#toast");

    window.clearTimeout(toastTimer);

    toast.textContent =
        "The shopping cart is our next feature. You can browse products now.";
    toast.hidden = false;

    toastTimer = window.setTimeout(() => {
        toast.hidden = true;
    }, 4500);
});

// ---------- Footer ----------

document.querySelector("#year").textContent = new Date().getFullYear();
filterProducts();