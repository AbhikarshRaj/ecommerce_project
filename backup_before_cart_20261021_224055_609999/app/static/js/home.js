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
// Python handles filtering using dictionary/set indexes. The browser renders results.
const searchInput = document.querySelector('#product-search');
searchInput.maxLength = 200;
const categoryButtons = [...document.querySelectorAll('.category-button')];
const subcategorySelect = document.querySelector('#subcategory-filter');
const resultCount = document.querySelector('#result-count');
const emptyState = document.querySelector('#empty-state');
const grid = document.querySelector('.product-grid');
const taxonomy = JSON.parse(document.querySelector('#store-taxonomy-data').textContent);
let selectedCategory = 'all';
let filterTimer;
let controller;

function imageFallbacks() {
    grid.querySelectorAll('img').forEach(image => {
        image.addEventListener('error', () => { image.hidden = true; });
        if (image.complete && image.naturalWidth === 0) image.hidden = true;
    });
}
function updateSubcategories() {
    subcategorySelect.replaceChildren(new Option('All subcategories', ''));
    taxonomy.subcategories.filter(s => selectedCategory === 'all' || String(s.category_id) === selectedCategory)
        .forEach(s => {
            const parent = taxonomy.categories.find(c => c.id === s.category_id);
            const label = selectedCategory === 'all' ? `${parent.name} / ${s.name}` : s.name;
            subcategorySelect.add(new Option(label, String(s.id)));
        });
}
async function filterProducts() {
    window.clearTimeout(filterTimer);
    if (controller) controller.abort();
    const currentController = new AbortController();
    controller = currentController;
    const parameters = new URLSearchParams({
        category: selectedCategory,
        subcategory: subcategorySelect.value,
        q: searchInput.value.trim()
    });
    grid.setAttribute('aria-busy', 'true');
    resultCount.textContent = 'Loading products…';
    try {
        const response = await fetch(`/api/catalog?${parameters}`, {signal: currentController.signal});
        if (!response.ok) throw new Error('Catalog request failed');
        const result = await response.json();
        if (controller !== currentController) return;
        // HTML is rendered by our Flask/Jinja template with automatic escaping.
        grid.innerHTML = result.html;
        resultCount.textContent = `${result.count} ${result.count === 1 ? 'product' : 'products'}`;
        emptyState.hidden = result.count !== 0;
        imageFallbacks();
    } catch (error) {
        if (error.name !== 'AbortError' && controller === currentController) {
            resultCount.textContent = 'Could not refresh products. Check Flask is running, then press Search to retry.';
        }
    } finally {
        if (controller === currentController) grid.setAttribute('aria-busy', 'false');
    }
}
function selectCategory(category) {
    selectedCategory = String(category);
    categoryButtons.forEach(button => {
        const active = button.dataset.category === selectedCategory;
        button.classList.toggle('active', active);
        button.setAttribute('aria-pressed', String(active));
    });
    updateSubcategories();
    filterProducts();
}
function scrollToProducts() {
    document.querySelector('#products').scrollIntoView({block: 'start'});
}
categoryButtons.forEach(button => button.addEventListener('click', () => {
    selectCategory(button.dataset.category);
    scrollToProducts();
}));
subcategorySelect.addEventListener('change', filterProducts);
searchInput.addEventListener('input', () => {
    if (controller) controller.abort();
    window.clearTimeout(filterTimer);
    filterTimer = window.setTimeout(filterProducts, 200);
});
document.querySelector('#search-form').addEventListener('submit', event => {
    event.preventDefault();
    filterProducts();
    scrollToProducts();
});
document.querySelector('#reset-filters').addEventListener('click', () => {
    searchInput.value = '';
    selectCategory('all');
    searchInput.focus();
});
document.querySelectorAll('[data-shop-category]').forEach(button => {
    button.addEventListener('click', () => {
        const category = taxonomy.categories.find(c => c.name.toLowerCase() === button.dataset.shopCategory);
        searchInput.value = '';
        selectCategory(category ? category.id : 'all');
        scrollToProducts();
    });
});
updateSubcategories();
imageFallbacks();

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