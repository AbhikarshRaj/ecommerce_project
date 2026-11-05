"use strict";

// ============================================================
// DSA: CIRCULAR BANNER CAROUSEL
// ============================================================

function getNextSlideIndex(current, count) {
    if (count <= 0) return 0;
    return (current + 1) % count;
}

function getPreviousSlideIndex(current, count) {
    if (count <= 0) return 0;
    return (current - 1 + count) % count;
}

// ============================================================
// IMAGE FALLBACKS
// ============================================================

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
    document.querySelectorAll(
        ".product-image, .cart-line-image img"
    ).forEach(applyImageFallback);
}

document.querySelectorAll("img").forEach(applyImageFallback);

// ============================================================
// SEARCH AND CATEGORY FILTERING
// ============================================================

const searchInput = document.querySelector("#product-search");

if (searchInput) {
    searchInput.maxLength = 200;
}

const categoryButtons = [
    ...document.querySelectorAll(".category-button")
];

const subcategorySelect = document.querySelector("#subcategory-filter");
const categoryFilterSelect = document.querySelector("#category-filter");
const resultCount = document.querySelector("#result-count");
const emptyState = document.querySelector("#empty-state");
const grid = document.querySelector(".product-grid");

const taxonomyElement = document.querySelector("#store-taxonomy-data");

const taxonomy = taxonomyElement
    ? JSON.parse(taxonomyElement.textContent)
    : { categories: [], subcategories: [] };

let selectedCategory = "all";
let filterTimer;
let controller;

function updateSubcategories() {
    if (!subcategorySelect) return;

    subcategorySelect.replaceChildren(
        new Option("All subcategories", "")
    );

    taxonomy.subcategories
        .filter((subcategory) =>
            selectedCategory === "all" ||
            String(subcategory.category_id) === selectedCategory
        )
        .forEach((subcategory) => {
            const parent = taxonomy.categories.find(
                (category) => category.id === subcategory.category_id
            );

            const label =
                selectedCategory === "all" && parent
                    ? `${parent.name} / ${subcategory.name}`
                    : subcategory.name;

            subcategorySelect.add(
                new Option(label, String(subcategory.id))
            );
        });
}

// ============================================================
// ADVANCED CATALOG FILTERS
// ============================================================

const filterPanel = document.querySelector("#catalog-filter-panel");
const toggleFilterPanel = document.querySelector("#toggle-filter-panel");
const filterPanelSummary = document.querySelector("#filter-panel-summary");
const filterSummaryText = document.querySelector("#filter-summary-text");
const editFiltersButton = document.querySelector("#edit-catalog-filters");
const closeFilterPanel = document.querySelector("#close-filter-panel");

const applyFiltersButton = document.querySelector(
    "#apply-catalog-filters"
);

const clearCatalogFiltersButton = document.querySelector(
    "#clear-catalog-filters"
);

const sortSelect = document.querySelector("#sort-filter");

const filterControls = {
    brand: document.querySelector("#brand-filter"),
    colour: document.querySelector("#colour-filter"),
    gender: document.querySelector("#gender-filter"),
    size: document.querySelector("#size-filter"),
    material: document.querySelector("#material-filter"),
    in_stock: document.querySelector("#stock-filter"),
    min_price: document.querySelector("#min-price-filter"),
    max_price: document.querySelector("#max-price-filter")
};

// Generate a summary of the currently selected filters.
function updateFilterSummary() {
    if (!filterSummaryText) return;

    const selectedFilters = [];

    // Category
    if (selectedCategory !== "all" && categoryFilterSelect) {
        const categoryName =
            categoryFilterSelect.selectedOptions[0]?.textContent.trim();

        if (categoryName) {
            selectedFilters.push(`Category: ${categoryName}`);
        }
    }

    // Subcategory
    if (subcategorySelect && subcategorySelect.value) {
        selectedFilters.push(
            `Subcategory: ${subcategorySelect.selectedOptions[0].textContent.trim()}`
        );
    }

    // Other dropdown filters
    const filterLabels = {
        brand: "Brand",
        colour: "Colour",
        gender: "Gender",
        size: "Size",
        material: "Material",
        in_stock: "Availability"
    };

    Object.entries(filterLabels).forEach(([key, label]) => {
        const control = filterControls[key];

        if (control && control.value) {
            selectedFilters.push(
                `${label}: ${control.selectedOptions[0]?.textContent.trim() || control.value}`
            );
        }
    });

    // Price range
    const minPrice = filterControls.min_price?.value;
    const maxPrice = filterControls.max_price?.value;

    if (minPrice) selectedFilters.push(`Min price: ₹${minPrice}`);
    if (maxPrice) selectedFilters.push(`Max price: ₹${maxPrice}`);

    filterSummaryText.textContent = selectedFilters.length
        ? selectedFilters.join(" | ")
        : "No filters selected";
}
function setFilterPanel(open) {
    if (!filterPanel || !toggleFilterPanel) return;

    // Show or hide the complete filter panel.
    filterPanel.hidden = !open;

    // Remove compact mode when opening the full panel.
    if (open) {
        filterPanel.classList.remove("is-compact");

        if (filterPanelSummary) {
            filterPanelSummary.hidden = true;
        }
    }

    toggleFilterPanel.setAttribute(
        "aria-expanded",
        String(open)
    );
}

// Reopen the full filter panel when Edit filters is clicked.
if (editFiltersButton) {
    editFiltersButton.addEventListener("click", () => {
        setFilterPanel(true);
    });
}

if (toggleFilterPanel) {
    toggleFilterPanel.addEventListener("click", () => {
        setFilterPanel(filterPanel.hidden);
    });
}

if (closeFilterPanel) {
    closeFilterPanel.addEventListener("click", () => {
        setFilterPanel(false);
    });
}

// Update a dropdown using the latest filter options from Flask.
function updateFilterSelect(select, values, placeholder) {
    if (!select) return;

    const previous = select.value;

    select.replaceChildren(
        new Option(placeholder, "")
    );

    (values || []).forEach((value) => {
        select.add(
            new Option(String(value), String(value))
        );
    });

    if ([...select.options].some(
        (option) => option.value === previous
    )) {
        select.value = previous;
    }
}

// Dynamic filter options depend on the current catalog results.
// Dynamic filter options depend on the current catalog results.
function updateDynamicFilterOptions(filters) {
    if (!filters) return;

    const dynamicFilters = [
        {
            key: "brand",
            values: filters.brands,
            placeholder: "All brands"
        },
        {
            key: "colour",
            values: filters.colours,
            placeholder: "All colours"
        },
        {
            key: "gender",
            values: filters.genders,
            placeholder: "All genders"
        },
        {
            key: "size",
            values: filters.sizes,
            placeholder: "All sizes"
        },
        {
            key: "material",
            values: filters.materials,
            placeholder: "All materials"
        }
    ];

    dynamicFilters.forEach((filter) => {
        const control = filterControls[filter.key];

        if (!control) return;

        const availableValues = filter.values || [];

        updateFilterSelect(
            control,
            availableValues,
            filter.placeholder
        );

        // Hide the filter when no products have this attribute.
        const field = control.closest(".filter-field");

        if (field) {
    const hasSelection = control.value !== "";

    field.hidden = availableValues.length === 0 && !hasSelection;
}
    });
}

function appendIfSelected(parameters, key, value) {
    if (
        value !== null &&
        value !== undefined &&
        String(value).trim() !== ""
    ) {
        parameters.set(key, String(value).trim());
    }
}

// ============================================================
// FETCH PRODUCTS FROM FLASK API
// ============================================================

async function filterProducts() {
    if (!grid || !resultCount) return;

    window.clearTimeout(filterTimer);

    if (controller) {
        controller.abort();
    }

    const currentController = new AbortController();
    controller = currentController;

    const parameters = new URLSearchParams();

    appendIfSelected(
        parameters,
        "category",
        selectedCategory === "all" ? "" : selectedCategory
    );

    appendIfSelected(
        parameters,
        "subcategory",
        subcategorySelect ? subcategorySelect.value : ""
    );

    appendIfSelected(
        parameters,
        "q",
        searchInput ? searchInput.value.trim() : ""
    );

    Object.entries(filterControls).forEach(([key, control]) => {
        if (control) {
            appendIfSelected(parameters, key, control.value);
        }
    });

    if (sortSelect) {
        appendIfSelected(
            parameters,
            "sort_by",
            sortSelect.value
        );
    }

    grid.setAttribute("aria-busy", "true");
    resultCount.textContent = "Loading products…";

    try {
        const response = await fetch(
            `/api/catalog?${parameters.toString()}`,
            { signal: currentController.signal }
        );

        if (!response.ok) {
            const detail = await response.json().catch(() => ({}));

            throw new Error(
                detail.description || "Catalog request failed"
            );
        }

        const result = await response.json();

        // Ignore responses from older requests.
        if (controller !== currentController) return;

        grid.innerHTML = result.html;

        resultCount.textContent =
            `${result.count} ${result.count === 1 ? "product" : "products"}`;

        if (emptyState) {
            emptyState.hidden = result.count !== 0;
        }

        updateDynamicFilterOptions(result.filters);
        imageFallbacks();

    } catch (error) {
        if (
            error.name !== "AbortError" &&
            controller === currentController
        ) {
            resultCount.textContent =
                error.message ||
                "Could not refresh products. Check Flask is running.";
        }

    } finally {
        if (controller === currentController) {
            grid.setAttribute("aria-busy", "false");
        }
    }
}

// ============================================================
// APPLY AND CLEAR FILTERS
// ============================================================

if (applyFiltersButton) {
    applyFiltersButton.addEventListener("click", () => {
        const min = filterControls.min_price?.value.trim();
        const max = filterControls.max_price?.value.trim();

        if (min && max && Number(min) > Number(max)) {
            filterControls.max_price.setCustomValidity(
                "Maximum price must be greater than or equal to minimum price."
            );

            filterControls.max_price.reportValidity();
            return;
        }

        if (filterControls.max_price) {
            filterControls.max_price.setCustomValidity("");
        }

        filterProducts();
        setFilterPanel(false);
    });
}

if (clearCatalogFiltersButton) {
    clearCatalogFiltersButton.addEventListener("click", () => {
        Object.values(filterControls).forEach((control) => {
            if (control) control.value = "";
        });

        if (sortSelect) sortSelect.value = "";
        if (subcategorySelect) subcategorySelect.value = "";

        filterProducts();
    });
}

if (sortSelect) {
    sortSelect.addEventListener("change", filterProducts);
}

// Update category when the user selects it from the filter panel.
if (categoryFilterSelect) {
    categoryFilterSelect.addEventListener("change", () => {
        const selectedValue = categoryFilterSelect.value || "all";

        // Reset subcategory when the category changes.
        if (subcategorySelect) {
            subcategorySelect.value = "";
        }

        selectCategory(selectedValue);
    });
}

// ============================================================
// CATEGORY SELECTION
// ============================================================

function selectCategory(category, updateHistory = true) {
    const previousCategory = selectedCategory;
    selectedCategory = String(category);

    // Reset category-dependent filters only when the category changes.
    if (previousCategory !== selectedCategory) {
        if (subcategorySelect) {
            subcategorySelect.value = "";
        }

        ["brand", "colour", "gender", "size", "material"].forEach((key) => {
            if (filterControls[key]) {
                filterControls[key].value = "";
            }
        });
    }

    // Keep the Category dropdown synchronized with the selected tab.
    if (categoryFilterSelect) {
        categoryFilterSelect.value =
            selectedCategory === "all" ? "" : selectedCategory;
    }

    categoryButtons.forEach((button) => {
        const active =
            button.dataset.category === selectedCategory;

        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", String(active));
    });

    document.querySelectorAll(".category-card").forEach((card) => {
        const isCurrent =
            card.dataset.categoryCard === selectedCategory;

        card.classList.toggle("active", isCurrent);
    });

    updateSubcategories();
    filterProducts();

    if (
        updateHistory &&
        window.history &&
        window.history.replaceState
    ) {
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
        productsSection.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }
}

// Category navigation tabs.
categoryButtons.forEach((button) => {
    button.addEventListener("click", () => {
        selectCategory(button.dataset.category);
        scrollToProducts();
    });
});

// Subcategory dropdown.
if (subcategorySelect) {
    subcategorySelect.addEventListener(
        "change",
        filterProducts
    );
}

// Search input with a short delay to avoid sending a request per keystroke.
if (searchInput) {
    searchInput.addEventListener("input", () => {
        if (controller) controller.abort();

        window.clearTimeout(filterTimer);

        filterTimer = window.setTimeout(
            filterProducts,
            200
        );
    });
}

// Search form submission.
const searchForm = document.querySelector("#search-form");

if (searchForm) {
    searchForm.addEventListener("submit", (event) => {
        event.preventDefault();
        filterProducts();
        scrollToProducts();
    });
}

// Reset all filters and search.
const resetFiltersBtn = document.querySelector("#reset-filters");

if (resetFiltersBtn) {
    resetFiltersBtn.addEventListener("click", () => {
        if (searchInput) searchInput.value = "";

        Object.values(filterControls).forEach((control) => {
            if (control) control.value = "";
        });

        if (sortSelect) sortSelect.value = "";

        selectCategory("all");

        if (searchInput) searchInput.focus();
    });
}

// Banner CTA buttons.
document.querySelectorAll("[data-shop-category]").forEach((button) => {
    button.addEventListener("click", () => {
        const targetSlug =
            button.dataset.shopCategory.toLowerCase();

        const category = taxonomy.categories.find(
            (item) =>
                item.name.toLowerCase() === targetSlug ||
                item.name.toLowerCase().includes(targetSlug)
        );

        if (searchInput) searchInput.value = "";

        selectCategory(category ? category.id : "all");
        scrollToProducts();
    });
});

// Category cards.
document.querySelectorAll("[data-category-card]").forEach((card) => {
    card.addEventListener("click", (event) => {
        event.preventDefault();

        const categoryId = card.dataset.categoryCard;

        if (searchInput) searchInput.value = "";

        selectCategory(categoryId);
        scrollToProducts();
    });
});

// Read category, search and subcategory from the URL.
function initializeFromUrlParameters() {
    const params = new URLSearchParams(window.location.search);

    const categoryQuery = params.get("category");
    const searchQuery = params.get("q");
    const subcategoryQuery = params.get("subcategory");

    if (searchQuery && searchInput) {
        searchInput.value = searchQuery;
    }

    if (categoryQuery) {
        const match = taxonomy.categories.find(
            (category) =>
                String(category.id) === categoryQuery ||
                category.name.toLowerCase() ===
                    categoryQuery.toLowerCase()
        );

        if (match) {
            selectedCategory = String(match.id);

            categoryButtons.forEach((button) => {
                const active =
                    button.dataset.category === selectedCategory;

                button.classList.toggle("active", active);
                button.setAttribute("aria-pressed", String(active));
            });

            updateSubcategories();

            if (subcategoryQuery && subcategorySelect) {
                subcategorySelect.value = subcategoryQuery;
            }

            filterProducts();
            return;
        }
    }

    updateSubcategories();
    filterProducts();
}

// ============================================================
// BANNER CAROUSEL
// ============================================================

const hero = document.querySelector(".hero");

const slides = hero
    ? [...hero.querySelectorAll(".slide")]
    : [];

const dots = hero
    ? [...hero.querySelectorAll(".slide-dot")]
    : [];

const toggleButton = document.querySelector("#toggle-slides");
const prevButton = document.querySelector("#previous-slide");
const nextButton = document.querySelector("#next-slide");

const reducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
);

let currentSlide = 0;
let timer = null;
let playing = !reducedMotion.matches;
let pointerInside = false;

function showSlide(index) {
    if (slides.length === 0) return;

    currentSlide =
        (index + slides.length) % slides.length;

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

        toggleButton.title = playing
            ? "Pause slideshow (Space)"
            : "Play slideshow (Space)";
    }

    if (
        playing &&
        !pointerInside &&
        !document.hidden &&
        slides.length > 1
    ) {
        timer = window.setInterval(() => {
            const nextIndex = getNextSlideIndex(
                currentSlide,
                slides.length
            );

            showSlide(nextIndex);
        }, 5000);
    }
}

if (prevButton) {
    prevButton.addEventListener("click", () => {
        const previousIndex = getPreviousSlideIndex(
            currentSlide,
            slides.length
        );

        showSlide(previousIndex);
        syncPlayback();
    });
}

if (nextButton) {
    nextButton.addEventListener("click", () => {
        const nextIndex = getNextSlideIndex(
            currentSlide,
            slides.length
        );

        showSlide(nextIndex);
        syncPlayback();
    });
}

dots.forEach((dot) => {
    dot.addEventListener("click", () => {
        const target = Number(dot.dataset.slide);

        if (!Number.isNaN(target)) {
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
    hero.addEventListener("mouseenter", () => {
        pointerInside = true;
        syncPlayback();
    });

    hero.addEventListener("mouseleave", () => {
        pointerInside = false;
        syncPlayback();
    });

    hero.addEventListener("keydown", (event) => {
        if (event.key === "ArrowLeft") {
            event.preventDefault();

            const previousIndex = getPreviousSlideIndex(
                currentSlide,
                slides.length
            );

            showSlide(previousIndex);
            syncPlayback();

        } else if (event.key === "ArrowRight") {
            event.preventDefault();

            const nextIndex = getNextSlideIndex(
                currentSlide,
                slides.length
            );

            showSlide(nextIndex);
            syncPlayback();
        }
    });

    hero.addEventListener("focusin", () => {
        if (playing) {
            playing = false;
            syncPlayback();
        }
    });
}

document.addEventListener(
    "visibilitychange",
    syncPlayback
);

reducedMotion.addEventListener("change", () => {
    if (reducedMotion.matches) {
        playing = false;
        syncPlayback();
    }
});

if (slides.length > 0) {
    showSlide(0);
    syncPlayback();
}
// ============================================================
// CONTACT FORM SUBMISSION
// ============================================================

const contactForm = document.querySelector("#contact-form");

const contactStatus = document.querySelector(
    "#contact-confirmation"
);

const contactSubmitBtn = document.querySelector(
    "#contact-submit-btn"
);

if (contactForm && contactStatus) {
    contactForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        const nameInput = document.querySelector("#contact-name");
        const emailInput = document.querySelector("#contact-email");
        const subjectInput = document.querySelector("#contact-subject");
        const messageInput = document.querySelector("#contact-message");

        const csrfTokenInput = contactForm.querySelector(
            'input[name="csrf_token"]'
        );

        const name = nameInput
            ? nameInput.value.trim()
            : "";

        const email = emailInput
            ? emailInput.value.trim()
            : "";

        const subject = subjectInput
            ? subjectInput.value.trim()
            : "";

        const message = messageInput
            ? messageInput.value.trim()
            : "";

        const csrf = csrfTokenInput
            ? csrfTokenInput.value
            : "";

        // Client-side validation.
        if (!name) {
            showContactAlert("Please enter your name.", true);

            if (nameInput) nameInput.focus();
            return;
        }

        if (!email || !email.includes("@")) {
            showContactAlert(
                "Please provide a valid email address.",
                true
            );

            if (emailInput) emailInput.focus();
            return;
        }

        if (!message || message.length < 5) {
            showContactAlert(
                "Please write a message with at least 5 characters.",
                true
            );

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
                message: message
            });

            const response = await fetch("/contact", {
                method: "POST",
                headers: {
                    "Content-Type":
                        "application/x-www-form-urlencoded"
                },
                body: formData
            });

            const data = await response.json();

            if (response.ok && data.success) {
                showContactAlert(
                    data.message ||
                    "Thank you! Your message has been sent successfully.",
                    false
                );

                contactForm.reset();

            } else {
                showContactAlert(
                    data.error ||
                    "Unable to send message. Please reload and try again.",
                    true
                );
            }

        } catch (error) {
            showContactAlert(
                "Connection error. Please check your network and try again.",
                true
            );

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

    contactStatus.className =
        `contact-confirmation ${isError ? "error" : "success"}`;

    contactStatus.innerHTML = `
        <div class="alert-icon" aria-hidden="true">
            ${isError ? "⚠️" : "✓"}
        </div>

        <div class="alert-content">
            <strong>
                ${isError ? "Unable to send" : "Message sent"}
            </strong>

            <p>${message}</p>
        </div>
    `;

    contactStatus.scrollIntoView({
        behavior: "smooth",
        block: "nearest"
    });
}

// ============================================================
// FOOTER YEAR AND INITIALIZATION
// ============================================================

const yearSpan = document.querySelector("#year");

if (yearSpan) {
    yearSpan.textContent = new Date().getFullYear();
}

// Initialize categories and filters using URL parameters.
initializeFromUrlParameters();