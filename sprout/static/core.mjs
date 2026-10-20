export const money = n => new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:2}).format(n/100);
export const countItems = items => items.reduce((s,i)=>s+i.quantity,0);
export const basketTotal = (items,products) => items.reduce((s,i)=>s+(products.find(p=>p.id===i.product_id)?.price||0)*i.quantity,0);
export function mergeCart(a,b){const m=new Map();for(const i of [...a,...b]) m.set(i.product_id,Math.min(20,(m.get(i.product_id)||0)+i.quantity));return [...m].map(([product_id,quantity])=>({product_id,quantity}));}
export function validCart(v){return Array.isArray(v)&&v.length<=50&&v.every(i=>i&&Number.isInteger(i.product_id)&&Number.isInteger(i.quantity)&&i.quantity>0&&i.quantity<=20);}
