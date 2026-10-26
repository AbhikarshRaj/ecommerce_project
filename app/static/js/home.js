"use strict";

// ============================================================================
// DATA STRUCTURES & ALGORITHMS (DSA): CIRCULAR BANNER CAROUSEL
// ============================================================================
// Requirement: Store banner entries in a list. Circular indexing supports next/previous:
//   next = (current + 1) % count;
//   previous = (current - 1 + count) % count;
// The '+ count' handles JavaScript remainder behavior for negative numbers.
// ============================================================================

/**
 * Calculate the next index using circular modulo indexing.
 * @param {number} current - Current zero-based index
 * @param {number} count - Total number of slides
 * @returns {number} Next index in the range [0, count - 1]
 */
function getNextSlideIndex(current, count) {
    if (count <= 0) return 0;
    return (current + 1) % count;
}

/**
 * Calculate the previous index using circular modulo indexing.
 * JavaScript's % operator is remainder, not modulo, so (-1 % 4) evaluates to -1.
 * Adding '+ count' before applying '% count' ensures the dividend is always positive.
 * @param {number} current - Current zero-based index
 * @param {number} count - Total number of slides
 * @returns {number} Previous index in the range [0, count - 1]
 */
function getPreviousSlideIndex(current, count) {
    if (count <= 0) return 0;
    return (current - 1 + count) % count;
}

// ---------- Missing images & Fallbacks ----------

const FALLBACK_IMAGE_URL = "/static/images/placeholder.png";

function applyImageFallback(image) {
    if (!image || image.dataset.hasFallback) return;
    image.dataset.hasFallback = "true";
    image.addEventListener("error", () => {
        image.src = FALLBACK_IMAGE_URL;
        image.classList.add("is-fallback");
        image.hidden = false;
    });

    if (image.complete && image.naturalWidth === 0) {
        image.src = FALLBACK_IMAGE_URL;
        image.classList.add("is-fallback");
        image.hidden = false;
    }
}

function imageFallbacks() {
    document.querySelectorAll(".product-image, .cart-line-image img").forEach(applyImageFallback);
}

// Initial fallback setup for existing images
document.querySelectorAll("img").forEach(applyImageFallback);

// ---------- Search and category filters ----------
// Python handles filtering using dictionary/set indexes. The browser renders results.
const searchInput = document.querySelector("#product-search");
if (searchInput) searchInput.maxLength = 200;

const categoryButtons = [...document.querySelectorAll(".category-button")];
const subcategorySelect = document.querySelector("#subcategory-filter");
const resultCount = document.querySelector("#result-count");
const emptyState = document.querySelector("#empty-state");
const grid = document.querySelector(".product-grid");

const taxonomyElement = document.querySelector("#store-taxonomy-data");
const taxonomy = taxonomyElement ? JSON.parse(taxonomyElement.textContent) : { categories: [], subcategories: [] };

let selectedCategory = "all";
let filterTimer;
let controller;

function updateSubcategories() {
    if (!subcategorySelect) return;
    subcategorySelect.replaceChildren(new Option("All subcategories", ""));
    taxonomy.subcategories
        .filter((s) => selectedCategory === "all" || String(s.category_id) === selectedCategory)
        .forEach((s) => {
            const parent = taxonomy.categories.find((c) => c.id === s.category_id);
            const label = selectedCategory === "all" && parent ? `${parent.name} / ${s.name}` : s.name;
            subcategorySelect.add(new Option(label, String(s.id)));
        });
}

/**
 * Fetch and display products according to search parameters.
 */
async function filterProducts() {
    if (!grid || !resultCount) return;
    window.clearTimeout(filterTimer);
    if (controller) controller.abort();

    const currentController = new AbortController();
    controller = currentController;

    const subcategoryVal = subcategorySelect ? subcategorySelect.value : "";
    const queryVal = searchInput ? searchInput.value.trim() : "";

    const parameters = new URLSearchParams({
        category: selectedCategory,
        subcategory: subcategoryVal,
        q: queryVal,
    });

    grid.setAttribute("aria-busy", "true");
    resultCount.textContent = "Loading products…";

    try {
        const response = await fetch(`/api/catalog?${parameters}`, { signal: currentController.signal });
        if (!response.ok) throw new Error("Catalog request failed");
        const result = await response.json();
        if (controller !== currentController) return;

        // HTML rendered safely by Flask/Jinja template with escaping
        grid.innerHTML = result.html;
        resultCount.textContent = `${result.count} ${result.count === 1 ? "product" : "products"}`;
        if (emptyState) emptyState.hidden = result.count !== 0;
        imageFallbacks();
    } catch (error) {
        if (error.name !== "AbortError" && controller === currentController) {
            resultCount.textContent = "Could not refresh products. Check Flask is running, then press Search to retry.";
        }
    } finally {
        if (controller === currentController) grid.setAttribute("aria-busy", "false");
    }
}

/**
 * Select a category and update active state across navigation buttons, category cards, and URL.
 * @param {string|number} category - Category ID or 'all'
 * @param {boolean} updateHistory - Whether to push/replace URL query param
 */
function selectCategory(category, updateHistory = true) {
    selectedCategory = String(category);

    categoryButtons.forEach((button) => {
        const active = button.dataset.category === selectedCategory;
        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", String(active));
    });

    // Update active highlight on category cards if present
    document.querySelectorAll(".category-card").forEach((card) => {
        const isCurrent = card.dataset.categoryCard === selectedCategory;
        card.classList.toggle("active", isCurrent);
    });

    updateSubcategories();
    filterProducts();

    if (updateHistory && window.history && window.history.replaceState) {
        const url = new URL(window.location);
        if (selectedCategory === "all") {
            url.searchParams.delete("category");
        } else {
            url.searchParams.set("category", selectedCategory);
        }
        window.history.replaceState({}, "", url.toString());
    }
}

function scrollToProducts() {
    const productsSection = document.querySelector("#products");
    if (productsSection) {
        productsSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }
}

// Setup category navigation tabs
categoryButtons.forEach((button) => {
    button.addEventListener("click", () => {
        selectCategory(button.dataset.category);
        scrollToProducts();
    });
});

if (subcategorySelect) {
    subcategorySelect.addEventListener("change", filterProducts);
}

if (searchInput) {
    searchInput.addEventListener("input", () => {
        if (controller) controller.abort();
        window.clearTimeout(filterTimer);
        filterTimer = window.setTimeout(filterProducts, 200);
    });
}

const searchForm = document.querySelector("#search-form");
if (searchForm) {
    searchForm.addEventListener("submit", (event) => {
        event.preventDefault();
        filterProducts();
        scrollToProducts();
    });
}

const resetFiltersBtn = document.querySelector("#reset-filters");
if (resetFiltersBtn) {
    resetFiltersBtn.addEventListener("click", () => {
        if (searchInput) searchInput.value = "";
        selectCategory("all");
        if (searchInput) searchInput.focus();
    });
}

// Connect Banner CTA buttons (`[data-shop-category]`)
document.querySelectorAll("[data-shop-category]").forEach((button) => {
    button.addEventListener("click", () => {
        const targetSlug = button.dataset.shopCategory.toLowerCase();
        const category = taxonomy.categories.find(
            (c) => c.name.toLowerCase() === targetSlug || c.name.toLowerCase().includes(targetSlug)
        );
        if (searchInput) searchInput.value = "";
        selectCategory(category ? category.id : "all");
        scrollToProducts();
    });
});

// Connect Category Cards (`[data-category-card]`)
document.querySelectorAll("[data-category-card]").forEach((card) => {
    card.addEventListener("click", (event) => {
        event.preventDefault();
        const catId = card.dataset.categoryCard;
        if (searchInput) searchInput.value = "";
        selectCategory(catId);
        scrollToProducts();
    });
});

// Parse initial URL query parameters (e.g. ?category=1 or ?category=electronics)
function initializeFromUrlParameters() {
    const params = new URLSearchParams(window.location.search);
    const catQuery = params.get("category");
    const searchQuery = params.get("q");
    const subcategoryQuery = params.get("subcategory");

    if (searchQuery && searchInput) {
        searchInput.value = searchQuery;
    }

    if (catQuery) {
        // Find matching category either by numeric ID or case-insensitive name
        const match = taxonomy.categories.find(
            (c) => String(c.id) === catQuery || c.name.toLowerCase() === catQuery.toLowerCase()
        );
        if (match) {
            selectCategory(match.id, false);
            if (subcategoryQuery && subcategorySelect) {
                subcategorySelect.value = subcategoryQuery;
            }
            return;
        }
    }

    updateSubcategories();
    filterProducts();
}

// ---------- Banner Carousel Implementation ----------

const hero = document.querySelector(".hero");
const slides = hero ? [...hero.querySelectorAll(".slide")] : [];
const dots = hero ? [...hero.querySelectorAll(".slide-dot")] : [];
const toggleButton = document.querySelector("#toggle-slides");
const prevButton = document.querySelector("#previous-slide");
const nextButton = document.querySelector("#next-slide");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

let currentSlide = 0;
let timer = null;
let playing = !reducedMotion.matches;
let pointerInside = false;

/**
 * Show slide at target index with circular boundary handling and accessibility updates.
 * @param {number} index - Index to display
 */
function showSlide(index) {
    if (slides.length === 0) return;

    // Boundary normalization using DSA circular index formula
    currentSlide = (index + slides.length) % slides.length;

    slides.forEach((slide, i) => {
        const isCurrent = i === currentSlide;
        slide.hidden = !isCurrent;
        if (isCurrent) {
            slide.setAttribute("tabindex", "0");
        } else {
            slide.removeAttribute("tabindex");
        }
    });

    dots.forEach((dot, i) => {
        const isCurrent = i === currentSlide;
        dot.classList.toggle("active", isCurrent);
        if (isCurrent) {
            dot.setAttribute("aria-current", "true");
        } else {
            dot.removeAttribute("aria-current");
        }
    });
}

function stopTimer() {
    if (timer !== null) {
        window.clearInterval(timer);
        timer = null;
    }
}

function syncPlayback() {
    stopTimer();

    if (toggleButton) {
        toggleButton.textContent = playing ? "Ⅱ" : "▶";
        toggleButton.setAttribute(
            "aria-label",
            playing ? "Pause slideshow" : "Play slideshow"
        );
        toggleButton.title = playing ? "Pause slideshow (Space)" : "Play slideshow (Space)";
    }

    if (playing && !pointerInside && !document.hidden && slides.length > 1) {
        timer = window.setInterval(() => {
            // DSA: Circular next = (current + 1) % count
            const nextIdx = getNextSlideIndex(currentSlide, slides.length);
            showSlide(nextIdx);
        }, 5000);
    }
}

if (prevButton) {
    prevButton.addEventListener("click", () => {
        // DSA: Circular previous = (current - 1 + count) % count
        const prevIdx = getPreviousSlideIndex(currentSlide, slides.length);
        showSlide(prevIdx);
        syncPlayback();
    });
}

if (nextButton) {
    nextButton.addEventListener("click", () => {
        // DSA: Circular next = (current + 1) % count
        const nextIdx = getNextSlideIndex(currentSlide, slides.length);
        showSlide(nextIdx);
        syncPlayback();
    });
}

dots.forEach((dot) => {
    dot.addEventListener("click", () => {
        const target = Number(dot.dataset.slide);
        if (!isNaN(target)) {
            showSlide(target);
            syncPlayback();
        }
    });
});

if (toggleButton) {
    toggleButton.addEventListener("click", () => {
        playing = !playing;
        syncPlayback();
    });
}

if (hero) {
    // Pause automatically when cursor enters; resume on leave
    hero.addEventListener("mouseenter", () => {
        pointerInside = true;
        syncPlayback();
    });

    hero.addEventListener("mouseleave", () => {
        pointerInside = false;
        syncPlayback();
    });

    // Keyboard navigation inside the carousel (ArrowLeft / ArrowRight)
    hero.addEventListener("keydown", (event) => {
        if (event.key === "ArrowLeft") {
            event.preventDefault();
            const prevIdx = getPreviousSlideIndex(currentSlide, slides.length);
            showSlide(prevIdx);
            syncPlayback();
        } else if (event.key === "ArrowRight") {
            event.preventDefault();
            const nextIdx = getNextSlideIndex(currentSlide, slides.length);
            showSlide(nextIdx);
            syncPlayback();
        }
    });

    // Pause on keyboard focus so user can read content comfortably
    hero.addEventListener("focusin", () => {
        if (playing) {
            playing = false;
            syncPlayback();
        }
    });
}

document.addEventListener("visibilitychange", syncPlayback);

reducedMotion.addEventListener("change", () => {
    if (reducedMotion.matches) {
        playing = false;
        syncPlayback();
    }
});

// Initialize carousel
if (slides.length > 0) {
    showSlide(0);
    syncPlayback();
}

// ---------- Contact Us Form Submission & Confirmation ----------

const contactForm = document.querySelector("#contact-form");
const contactStatus = document.querySelector("#contact-confirmation");
const contactSubmitBtn = document.querySelector("#contact-submit-btn");

if (contactForm && contactStatus) {
    contactForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        const nameInput = document.querySelector("#contact-name");
        const emailInput = document.querySelector("#contact-email");
        const subjectInput = document.querySelector("#contact-subject");
        const messageInput = document.querySelector("#contact-message");
        const csrfTokenInput = contactForm.querySelector('input[name="csrf_token"]');

        const name = nameInput ? nameInput.value.trim() : "";
        const email = emailInput ? emailInput.value.trim() : "";
        const subject = subjectInput ? subjectInput.value.trim() : "";
        const message = messageInput ? messageInput.value.trim() : "";
        const csrf = csrfTokenInput ? csrfTokenInput.value : "";

        // Client validation
        if (!name) {
            showContactAlert("Please enter your name.", true);
            if (nameInput) nameInput.focus();
            return;
        }

        if (!email || !email.includes("@")) {
            showContactAlert("Please provide a valid email address.", true);
            if (emailInput) emailInput.focus();
            return;
        }

        if (!message || message.length < 5) {
            showContactAlert("Please write a message with at least 5 characters.", true);
            if (messageInput) messageInput.focus();
            return;
        }

        if (contactSubmitBtn) {
            contactSubmitBtn.disabled = true;
            contactSubmitBtn.classList.add("submitting");
        }

        try {
            const formData = new URLSearchParams({
                csrf_token: csrf,
                name: name,
                email: email,
                subject: subject,
                message: message,
            });

            const response = await fetch("/contact", {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: formData,
            });

            const data = await response.json();

            if (response.ok && data.success) {
                showContactAlert(data.message || "Thank you! Your message has been sent successfully.", false);
                contactForm.reset();
            } else {
                showContactAlert(data.error || "Unable to send message. Please reload and try again.", true);
            }
        } catch (error) {
            showContactAlert("Connection error. Please check your network and try again.", true);
        } finally {
            if (contactSubmitBtn) {
                contactSubmitBtn.disabled = false;
                contactSubmitBtn.classList.remove("submitting");
            }
        }
    });
}

function showContactAlert(message, isError) {
    if (!contactStatus) return;
    contactStatus.hidden = false;
    contactStatus.className = `contact-confirmation ${isError ? "error" : "success"}`;
    contactStatus.innerHTML = `
        <div class="alert-icon" aria-hidden="true">${isError ? "⚠️" : "✓"}</div>
        <div class="alert-content">
            <strong>${isError ? "Unable to send" : "Message sent"}</strong>
            <p>${message}</p>
        </div>
    `;
    contactStatus.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// ---------- Footer dynamic year & initial load ----------

const yearSpan = document.querySelector("#year");
if (yearSpan) {
    yearSpan.textContent = new Date().getFullYear();
}

// Initialize categories and filters based on URL
initializeFromUrlParameters();
