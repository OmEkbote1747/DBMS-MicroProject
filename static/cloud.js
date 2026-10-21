const $ = s => document.querySelector(s);
const state = { client: null, user: null, role: null, products: [], cart: new Map() };
const money = paise => new Intl.NumberFormat('en-IN', {style:'currency',currency:'INR'}).format(paise / 100);
const escapeHtml = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function notice(message, type='') { const n=$('#notice'); n.textContent=message; n.className=`cloud-status ${type}`; }
function toast(message) { const n=$('#toast'); n.textContent=message; n.classList.add('show'); setTimeout(()=>n.classList.remove('show'),2800); }
function showRole() {
  $('#account-label').textContent=state.user?.email || 'Signed out';
  $('#role-badge').textContent=state.role ? state.role.toUpperCase() : state.user ? 'PROFILE NEEDED' : 'GUEST';
  $('#auth-button').textContent=state.user ? 'Sign out' : 'Sign in';
  $('#auth-panel').classList.toggle('hidden',!!state.user);
  $('#catalogue-panel').classList.toggle('hidden',!state.client);
  $('#orders-panel').classList.toggle('hidden',!state.user);
  $('#admin-panel').classList.toggle('hidden',state.role!=='admin');
  $('#denied-panel').classList.toggle('hidden',!['customer','inventory','analyst'].includes(state.role));
}
async function loadProfile() {
  state.role=null;
  if(state.user){
    const {data,error}=await state.client.from('profiles').select('full_name,role').eq('id',state.user.id).single();
    if(error) throw error;
    state.role=data.role;
    $('#account-label').textContent=data.full_name || state.user.email;
  }
  showRole();
}
async function loadProducts() {
  const {data,error}=await state.client.from('products').select('id,name,description,price_paise,stock_quantity,categories(name)').eq('is_active',true).order('name');
  if(error) throw error;
  state.products=data.map(p=>({...p,category:p.categories?.name || 'Uncategorised'}));
  renderProducts();
}
function renderProducts() {
  const term=$('#search').value.toLowerCase();
  const products=state.products.filter(p=>`${p.name} ${p.category} ${p.description}`.toLowerCase().includes(term));
  $('#product-count').textContent=`${products.length} products`;
  $('#products').innerHTML=products.map(p=>{
    const amount=state.cart.get(p.id)||0;
    const canBuy=state.role==='customer' && p.stock_quantity>0;
    const canStock=['inventory','admin'].includes(state.role);
    return `<article class="product-card"><div class="product-body"><div class="category-label">${escapeHtml(p.category)}</div><h3>${escapeHtml(p.name)}</h3><p>${escapeHtml(p.description)}</p><div class="price-row"><strong>${money(p.price_paise)}</strong><span class="stock ${p.stock_quantity<10?'low':''}">${p.stock_quantity} in stock</span></div>${canBuy?`<button class="primary-button add-cart" data-id="${p.id}">${amount?'Add one · '+amount+' in cart':'Add to cart'}</button>`:''}${canStock?`<label class="stock-edit">Set stock <input type="number" min="0" value="${p.stock_quantity}" data-stock="${p.id}"><button class="save-stock" data-id="${p.id}">Save</button></label>`:''}</div></article>`;
  }).join('')||'<p class="empty-state">No matching products.</p>';
  if(state.role==='customer') $('#products').insertAdjacentHTML('beforeend',`<div class="cart-bar"><span>${[...state.cart.values()].reduce((a,b)=>a+b,0)} items in cart</span><button id="place-order" class="primary-button" ${state.cart.size?'':'disabled'}>Place order</button></div>`);
  document.querySelectorAll('.add-cart').forEach(b=>b.onclick=()=>{const id=Number(b.dataset.id);state.cart.set(id,(state.cart.get(id)||0)+1);renderProducts();});
  document.querySelectorAll('.save-stock').forEach(b=>b.onclick=async()=>{
    const stock=Number(document.querySelector(`[data-stock="${b.dataset.id}"]`).value);
    try { const {error}=await state.client.rpc('update_stock',{p_product_id:Number(b.dataset.id),p_stock_quantity:stock}); if(error)throw error; await loadProducts(); toast('Stock updated by the database function.'); }
    catch(e){notice(e.message,'error');}
  });
  $('#place-order')?.addEventListener('click',placeOrder);
}
async function loadOrders() {
  if(!state.user)return;
  const {data,error}=await state.client.from('orders').select('id,customer_id,status,total_paise,created_at,order_items(product_id,quantity,unit_price_paise)').order('created_at',{ascending:false});
  if(error)throw error;
  $('#orders-title').textContent=state.role==='customer'?'Your orders':state.role==='analyst'?'Order data · read only':'Recent orders';
  $('#orders').innerHTML=data.length?data.map(o=>`<article class="order-card"><div class="order-meta"><div><span class="eyebrow">ORDER #${o.id}</span><small>Customer ID: ${escapeHtml(o.customer_id)}</small></div><span class="status">${escapeHtml(o.status)}</span></div><div class="order-items">${(o.order_items||[]).map(i=>{const p=state.products.find(x=>x.id===i.product_id);return `<span>${escapeHtml(p?.name||'Product')} × ${i.quantity}</span>`}).join('')}</div><strong>${money(o.total_paise)}</strong><small>${escapeHtml(o.created_at)}</small></article>`).join(''):'<p class="empty-state">No orders yet.</p>';
}
async function placeOrder() {
  const items=[...state.cart].map(([product_id,quantity])=>({product_id,quantity}));
  const {data,error}=await state.client.rpc('place_order',{p_items:items});
  if(error){notice(error.message,'error');return;}
  state.cart.clear();await loadProducts();await loadOrders();toast(`Order #${data} saved. PostgreSQL updated stock.`);
}
async function connect(url,key) {
  if(!window.supabase?.createClient) throw new Error('Could not load the Supabase client library. Check your internet connection and reload.');
  state.client=window.supabase.createClient(url,key);
  const {data:{session},error}=await state.client.auth.getSession();
  if(error)throw error;
  state.user=session?.user||null;
  $('#setup').classList.add('hidden');showRole();
  await loadProducts();if(state.user)await loadProfile();
  state.client.auth.onAuthStateChange((_event,sessionNow)=>{
    state.user=sessionNow?.user||null;
    setTimeout(async()=>{try{await loadProfile();await loadProducts();if(state.user)await loadOrders();else $('#orders-panel').classList.add('hidden');}catch(e){notice(e.message,'error');}},0);
  });
  notice('Connected to Supabase. Product and order requests go to PostgreSQL and are subject to its grants and RLS policies.','ok');
  if(state.user) await loadOrders();
}
$('#config-form').onsubmit=async e=>{
  e.preventDefault();const f=new FormData(e.currentTarget);const url=String(f.get('url')).replace(/\/$/,'');const key=String(f.get('key')).trim();
  try{await connect(url,key);localStorage.setItem('amazonSupabaseConfig',JSON.stringify({url,key}));}
  catch(err){state.client=null;notice(err.message,'error');$('#setup').classList.remove('hidden');}
};
$('#login-form').onsubmit=async e=>{
  e.preventDefault();const f=new FormData(e.currentTarget);
  const {error}=await state.client.auth.signInWithPassword({email:f.get('email'),password:f.get('password')});
  if(error)notice(error.message,'error');else{e.currentTarget.reset();notice('Signed in. The database profile determines the role.','ok');}
};
$('#auth-button').onclick=async()=>{
  if(state.user){const {error}=await state.client.auth.signOut();if(error)notice(error.message,'error');else{state.user=null;state.role=null;state.cart.clear();showRole();$('#orders-panel').classList.add('hidden');renderProducts();}}
  else $('#auth-panel').scrollIntoView({behavior:'smooth'});
};
$('#search').oninput=renderProducts;
$('#refresh-orders').onclick=()=>loadOrders().catch(e=>notice(e.message,'error'));
$('#try-denied').onclick=async()=>{
  let result;
  if(state.role==='customer'){
    const p=state.products[0];
    if(!p){notice('No product is available for the permission demonstration.','error');return;}
    result=await state.client.rpc('update_stock',{p_product_id:p.id,p_stock_quantity:p.stock_quantity});
  } else {
    result=await state.client.rpc('admin_add_product',{p_name:'Permission test product',p_category:'Demo',p_description:'Should be rejected for this role',p_price_paise:100,p_stock_quantity:1});
  }
  if(result.error)notice(`PostgreSQL rejected the request for this role: ${result.error.message}`,'error');
  else notice('The request was unexpectedly allowed. Review the Supabase role policy and function grants.','error');
};
$('#add-product-form').onsubmit=async e=>{
  e.preventDefault();const f=new FormData(e.currentTarget);
  const {error}=await state.client.rpc('admin_add_product',{p_name:f.get('name'),p_category:f.get('category'),p_description:f.get('description'),p_price_paise:Math.round(Number(f.get('price_rupees'))*100),p_stock_quantity:Number(f.get('stock_quantity'))});
  if(error){notice(error.message,'error');return;}e.currentTarget.reset();await loadProducts();toast('Product added by the database function.');
};
(async()=>{
  const saved=localStorage.getItem('amazonSupabaseConfig');
  if(saved){try{const c=JSON.parse(saved);$('#config-form [name="url"]').value=c.url;$('#config-form [name="key"]').value=c.key;await connect(c.url,c.key);}catch(e){notice(`Could not reconnect: ${e.message}`,'error');$('#setup').classList.remove('hidden');}}
})();
