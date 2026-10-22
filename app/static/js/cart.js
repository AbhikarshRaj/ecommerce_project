"use strict";
(() => {
    let state = null;
    let busy = false;
    let ready = false;
    let toastTimer;
    const page = document.querySelector('[data-cart-page]');
    const badge = document.querySelector('.cart-count');
    const cartButton = document.querySelector('#cart-button');
    const money = paise => new Intl.NumberFormat('en-IN', {style:'currency', currency:'INR'}).format(paise / 100);
    const node = (tag, className, text) => {
        const element = document.createElement(tag);
        if (className) element.className = className;
        if (text !== undefined) element.textContent = text;
        return element;
    };
    function notify(message, error = false) {
        const element = document.querySelector(page ? '#cart-message' : '#toast');
        if (!element) return;
        element.textContent = message;
        element.hidden = false;
        element.classList.toggle('error', error);
        if (!page) {
            window.clearTimeout(toastTimer);
            toastTimer = window.setTimeout(() => { element.hidden = true; }, 6000);
        }
    }
    function controls() {
        const byId = new Map((state?.items || []).map(item => [item.id,item]));
        document.querySelectorAll('.product-cart-controls').forEach(group => {
            const item = byId.get(group.dataset.cartProduct);
            const quantity = item?.quantity || 0;
            const stock = item ? item.stock : Number(group.dataset.stock);
            group.querySelector('.add-cart-button').hidden = quantity > 0;
            group.querySelector('.product-stepper').hidden = quantity === 0;
            group.querySelector('.product-cart-quantity').textContent = quantity;
            group.querySelectorAll('button').forEach(button => {
                button.disabled = !ready || busy || (['add','increment'].includes(button.dataset.cartAction) && quantity >= Math.min(stock,999));
            });
        });
        if (page) {
            document.querySelectorAll('[data-cart-action]').forEach(button => {
                const action = button.dataset.cartAction;
                const item = byId.get(button.dataset.productId);
                button.disabled = !ready || busy ||
                    (action === 'undo' && !state?.can_undo) || (action === 'redo' && !state?.can_redo) ||
                    (action === 'increment' && (!item || item.quantity >= Math.min(item.stock,999) || item.unavailable));
            });
            document.querySelectorAll('[data-cart-quantity]').forEach(input => { input.disabled = busy || !ready; });
            document.querySelector('#clear-cart').disabled = busy || !ready || !state?.count;
        }
    }
    function actionButton(action, id, text, label, className = '') {
        const button = node('button', className, text);
        button.type = 'button';
        button.dataset.cartAction = action;
        button.dataset.productId = id;
        button.setAttribute('aria-label', label);
        return button;
    }
    function render() {
        if (!state) return;
        if (badge) badge.textContent = state.count;
        cartButton?.setAttribute('aria-label', `Shopping cart, ${state.count} items`);
        if (page) {
            const active = document.activeElement;
            const focusedId = active?.dataset.productId;
            const focusedAction = active?.dataset.cartAction;
            const wasInput = active?.hasAttribute('data-cart-quantity');
            document.querySelector('#cart-loading').hidden = true;
            document.querySelector('#cart-retry').hidden = true;
            document.querySelector('#cart-empty').hidden = state.items.length > 0;
            document.querySelector('#cart-layout').hidden = state.items.length === 0;
            document.querySelector('#cart-item-label').textContent = `${state.count} ${state.count === 1 ? 'item' : 'items'} · ${state.distinct_count} products`;
            const list = document.querySelector('#cart-items');
            list.replaceChildren();
            state.items.forEach(item => {
                const article = node('article','cart-line');
                const picture = node('div','cart-line-image');
                if (item.image_path) {
                    const image = document.createElement('img');
                    image.src = '/static/' + item.image_path;
                    image.alt = item.name;
                    image.addEventListener('error', () => { picture.textContent = item.name.charAt(0); });
                    picture.append(image);
                } else picture.textContent = '?';
                const info = node('div','cart-line-info');
                info.append(node('h2','',item.name),node('p','',`${money(item.price_paise)} each`));
                if (item.unavailable) info.append(node('p','item-warning','Unavailable. Remove this item.'));
                else if (item.exceeds_stock) info.append(node('p','item-warning',`Only ${item.stock} available. Reduce the quantity or remove this item.`));
                else info.append(node('p','',`${item.stock} available`));
                const actions = node('div','cart-line-actions');
                const stepper = node('div','quantity-stepper');
                stepper.append(actionButton('decrement',item.id,'−',`Decrease ${item.name} quantity`));
                const quantity = document.createElement('input');
                quantity.type='number'; quantity.min='0'; quantity.max=String(Math.min(item.stock,999)); quantity.step='1';
                quantity.value=String(item.quantity); quantity.dataset.cartQuantity=''; quantity.dataset.productId=item.id;
                quantity.setAttribute('aria-label',`Quantity for ${item.name}; enter zero to remove`);
                stepper.append(quantity,actionButton('increment',item.id,'+',`Increase ${item.name} quantity`));
                actions.append(stepper,actionButton('remove',item.id,'Remove',`Remove ${item.name}`,'remove-cart-item'));
                info.append(actions);
                article.append(picture,info,node('div','line-price',money(item.line_total_paise)));
                list.append(article);
            });
            document.querySelector('#cart-subtotal').textContent = money(state.subtotal_paise);
            document.querySelector('#cart-total').textContent = money(state.subtotal_paise);
            const undo = document.querySelector('[data-cart-action="undo"]');
            const redo = document.querySelector('[data-cart-action="redo"]');
            undo.title = state.undo_label ? `Undo ${state.undo_label}` : 'Nothing to undo';
            redo.title = state.redo_label ? `Redo ${state.redo_label}` : 'Nothing to redo';
            document.querySelector('#cart-history-list').replaceChildren(...state.history.map(label => node('li','',label)));
            if (focusedId) {
                const target = [...list.querySelectorAll('[data-product-id]')].find(element => element.dataset.productId === focusedId &&
                    (wasInput ? element.hasAttribute('data-cart-quantity') : element.dataset.cartAction === focusedAction));
                // Controls become enabled in controls() after the request finishes.
                if (target) { target.disabled = false; target.focus({preventScroll:true}); }
                else { undo.disabled = false; undo.focus({preventScroll:true}); }
            }
        }
        controls();
    }
    async function refresh() {
        if (busy) return;
        busy = true; controls();
        try {
            const response = await fetch('/api/cart', {cache:'no-store'});
            if (!response.ok) throw new Error('Unable to load cart');
            state = await response.json(); ready = true; render();
        } catch (_error) {
            ready = false;
            notify('Could not load your cart. Check Flask is running and reload the page.', true);
            if (page) {
                document.querySelector('#cart-loading').hidden = true;
                document.querySelector('#cart-retry').hidden = false;
            }
        } finally { busy = false; controls(); }
    }
    async function change(action, productId = '', quantity = '') {
        if (!ready || busy || !state) return;
        const activeBefore = document.activeElement;
        const focusSpec = activeBefore?.dataset.productId ? {
            id: activeBefore.dataset.productId,
            action: activeBefore.dataset.cartAction,
            input: activeBefore.hasAttribute('data-cart-quantity')
        } : null;
        busy = true; controls();
        try {
            const body = new URLSearchParams({action,product_id:productId,quantity,version:String(state.version),csrf_token:state.csrf_token});
            const response = await fetch('/api/cart/action', {method:'POST',body});
            if (!response.headers.get('content-type')?.includes('application/json')) {
                throw new Error('Session expired. Reload the page and try again.');
            }
            const result = await response.json();
            if (Array.isArray(result.items)) { state = result; render(); }
            else if (!response.ok) throw new Error(result.error || 'Unable to save cart. Reload before retrying.');
            notify(result.error || result.message || 'Cart updated.', !response.ok);
        } catch (error) {
            ready = false;
            notify(error.message || 'Connection interrupted. Reload to check your cart before retrying.', true);
            if (page) document.querySelector('#cart-retry').hidden = false;
        } finally {
            busy = false; controls();
            if (focusSpec) {
                const targets = [...document.querySelectorAll('[data-product-id]')]
                    .filter(element => element.dataset.productId === focusSpec.id && !element.disabled && !element.closest('[hidden]'));
                const exact = targets.find(element => focusSpec.input ? element.hasAttribute('data-cart-quantity') : element.dataset.cartAction === focusSpec.action);
                const fallback = page ? document.querySelector('[data-cart-action="undo"]') : null;
                const target = exact || targets[0] || fallback;
                if (target && !target.disabled) target.focus({preventScroll:true});
            }
        }
    }
    document.addEventListener('click', event => {
        const button = event.target.closest('[data-cart-action]');
        if (button && !button.disabled) change(button.dataset.cartAction,button.dataset.productId || '');
    });
    document.addEventListener('change', event => {
        if (event.target.matches('[data-cart-quantity]')) {
            const input = event.target;
            if (!input.checkValidity() || input.value === '') { input.reportValidity(); return; }
            change('set',input.dataset.productId,input.value);
        }
    });
    if (cartButton && cartButton.tagName === 'BUTTON') cartButton.addEventListener('click', () => { window.location.href='/cart'; });
    const grid = document.querySelector('.product-grid');
    if (grid) new MutationObserver(controls).observe(grid,{childList:true});
    if (page) {
        const dialog = document.querySelector('#clear-dialog');
        document.querySelector('#clear-cart').addEventListener('click', () => {
            dialog.returnValue = 'cancel'; dialog.showModal();
        });
        dialog.addEventListener('close', () => { if (dialog.returnValue === 'confirm') change('clear'); });
        document.querySelector('#cart-retry').addEventListener('click',refresh);
    }
    window.addEventListener('focus',refresh);
    refresh();
})();
