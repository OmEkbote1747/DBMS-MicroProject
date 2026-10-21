const state = { user: null, products: [], cart: new Map() };
const $ = (s) => document.querySelector(s);
const money = (paise) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(paise / 100);
async function api(path, options = {}) {
  const response = await fetch(path, { credentials: 'same-origin', ...options, headers: { 'Content-Type': 'application/json', ...(options.headers || {}) } });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Something went wrong');
  return data;
}
function toast(message) { const el = $('#toast'); el.textContent = message; el.classList.add('show'); setTimeout(() => el.classList.remove('show'), 2800); }
function roleName(role) { return ({ customer: 'CUSTOMER', inventory: 'INVENTORY STAFF', analyst: 'ANALYST', admin: 'ADMINISTRATOR' })[role] || 'GUEST'; }
function renderProducts() {
  const term = $('#search').value.toLowerCase();
  const items = state.products.filter(p => `${p.name} ${p.category} ${p.description}`.toLowerCase().includes(term));
  $('#results-label').textContent = term ? `${items.length} search results` : 'All products';
  $('#product-count').textContent = state.products.length;
  $('#products').innerHTML = items.map((p, i) => {
    const count = state.cart.get(p.id) || 0;
    const canBuy = state.user?.role === 'customer' && p.stock_quantity > 0;
    const canEdit = ['inventory', 'admin'].includes(state.user?.role);
    return `<article class="product-card"><div class="product-art art-${i % 5}"><span>${p.category}</span><div>${['◉','⌁','◍','▤','◌'][i % 5]}</div><small>STOREFRONT SAMPLE</small></div><div class="product-body"><div class="category-label">${p.category}</div><h3>${escapeHtml(p.name)}</h3><p>${escapeHtml(p.description)}</p><div class="price-row"><strong>${money(p.price_paise)}</strong><span class="stock ${p.stock_quantity < 10 ? 'low' : ''}">${p.stock_quantity} in stock</span></div>${canBuy ? `<button class="primary-button add-cart" data-id="${p.id}">${count ? `Add one · ${count} in cart` : 'Add to cart'}</button>` : ''}${canEdit ? `<label class="stock-edit">Update stock <input type="number" min="0" value="${p.stock_quantity}" data-stock-id="${p.id}"><button class="save-stock" data-id="${p.id}">Save</button></label>` : ''}</div></article>`;
  }).join('') || '<p class="empty-state">No matching products. Try another search.</p>';
  if (state.user?.role === 'customer') $('#products').insertAdjacentHTML('beforeend', `<div class="cart-bar"><span><b>${[...state.cart.values()].reduce((a,b)=>a+b,0)}</b> items in your cart</span><button id="place-order" class="primary-button" ${state.cart.size ? '' : 'disabled'}>Place order</button></div>`);
  document.querySelectorAll('.add-cart').forEach(b => b.onclick = () => { const id = Number(b.dataset.id); state.cart.set(id, (state.cart.get(id) || 0) + 1); renderProducts(); });
  document.querySelectorAll('.save-stock').forEach(b => b.onclick = async () => { const id = Number(b.dataset.id); const stock = Number(document.querySelector(`[data-stock-id="${id}"]`).value); try { await api(`/api/products/${id}/stock`, { method: 'PATCH', body: JSON.stringify({ stock_quantity: stock }) }); await loadProducts(); toast('Stock quantity saved to the database.'); } catch (e) { toast(e.message); } });
  $('#place-order')?.addEventListener('click', placeOrder);
}
function escapeHtml(value) { return String(value).replace(/[&<>"']/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c])); }
async function loadProducts() { state.products = await api('/api/products'); renderProducts(); }
async function loadOrders() {
  if (!state.user) return;
  try {
    const orders = await api('/api/orders');
    $('#order-panel').classList.remove('hidden');
    $('#orders-title').textContent = state.user.role === 'customer' ? 'Your orders' : state.user.role === 'analyst' ? 'Order data (read only)' : 'Recent orders';
    $('#orders').innerHTML = orders.length ? orders.map(o => `<article class="order-card"><div class="order-meta"><div><span class="eyebrow">ORDER #${o.id}</span><b>${escapeHtml(o.customer)}</b></div><span class="status">${escapeHtml(o.status)}</span></div><div class="order-items">${o.items.map(i => `<span>${escapeHtml(i.name)} × ${i.quantity}</span>`).join('')}</div><strong>${money(o.total_paise)}</strong><small>${escapeHtml(o.created_at)}</small></article>`).join('') : '<p class="empty-state">No orders yet. Add a product to the cart and place your first demo order.</p>';
  } catch (e) { $('#order-panel').classList.add('hidden'); }
}
async function placeOrder() {
  try {
    const result = await api('/api/orders', { method: 'POST', body: JSON.stringify({ items: [...state.cart.entries()].map(([product_id, quantity]) => ({ product_id, quantity })) }) });
    state.cart.clear(); await loadProducts(); await loadOrders(); toast(`Order #${result.order_id} saved. Stock was updated.`);
  } catch (e) { toast(e.message); }
}
function renderUser() {
  $('#account-label').textContent = state.user ? state.user.full_name : 'Signed out';
  $('#role-badge').textContent = roleName(state.user?.role);
  $('#auth-button').textContent = state.user ? 'Sign out' : 'Sign in';
  $('#login-panel').classList.toggle('hidden', !!state.user);
  $('#admin-panel').classList.toggle('hidden', state.user?.role !== 'admin');
  $('#order-panel').classList.toggle('hidden', !state.user);
  loadProducts(); loadOrders();
}
$('#auth-button').onclick = async () => {
  if (state.user) { await api('/api/logout', { method: 'POST', body: '{}' }); state.user = null; state.cart.clear(); renderUser(); toast('Signed out.'); }
  else { $('#login-panel').scrollIntoView({ behavior: 'smooth', block: 'center' }); $('#login-panel').classList.remove('hidden'); }
};
document.querySelectorAll('.login-choice').forEach(b => b.onclick = async () => {
  try { const result = await api('/api/login', { method: 'POST', body: JSON.stringify({ email: b.dataset.email, password: b.dataset.password }) }); state.user = result.user; renderUser(); toast(`Signed in as ${roleName(state.user.role).toLowerCase()}.`); }
  catch (e) { toast(e.message); }
});
$('#search').oninput = renderProducts;
$('#refresh-orders').onclick = loadOrders;
$('#add-product-form').onsubmit = async (event) => {
  event.preventDefault(); const body = Object.fromEntries(new FormData(event.currentTarget));
  try { await api('/api/products', { method: 'POST', body: JSON.stringify(body) }); event.currentTarget.reset(); await loadProducts(); toast('New product added.'); }
  catch (e) { toast(e.message); }
};
(async () => { const result = await api('/api/me'); state.user = result.user; renderUser(); })();
