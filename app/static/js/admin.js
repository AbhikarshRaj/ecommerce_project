"use strict";
const dataElement = document.querySelector('#admin-taxonomy-data');
if (dataElement) {
    const data = JSON.parse(dataElement.textContent);
    const normalize = (value) => value.normalize('NFKC').trim().replace(/\s+/g, ' ').toLowerCase();
    document.querySelectorAll('.taxonomy-fields').forEach((group) => {
        const category = group.querySelector('[name="category"]');
        const subcategory = group.querySelector('[name="subcategory"]');
        const options = group.querySelector('datalist');
        function updateSuggestions() {
            const selected = data.categories.find(c => normalize(c.name) === normalize(category.value));
            options.replaceChildren();
            data.subcategories.filter(s => selected && s.category_id === selected.id).forEach(s => {
                const option = document.createElement('option');
                option.value = s.name;
                options.append(option);
            });
        }
        category.addEventListener('input', () => {
            subcategory.value = '';
            updateSuggestions();
        });
        updateSuggestions();
    });
}
const upload = document.querySelector('#image');
if (upload) {
    let previewUrl;
    const preview = document.querySelector('#image-preview');
    upload.addEventListener('change', () => {
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        upload.setCustomValidity('');
        preview.hidden = true;
        const file = upload.files[0];
        if (!file) return;
        if (file.size > 5 * 1024 * 1024) {
            upload.setCustomValidity('Choose an image no larger than 5 MB.');
            upload.reportValidity();
            return;
        }
        previewUrl = URL.createObjectURL(file);
        preview.onload = () => { preview.hidden = false; };
        preview.onerror = () => { preview.hidden = true; };
        preview.src = previewUrl;
    });
}
