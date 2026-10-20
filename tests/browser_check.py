"""Actual Chromium E2E against a disposable demo DB, invoked by scripts/check_browser.py."""
import json, time, os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
base=os.getenv('SPROUT_TEST_URL','http://127.0.0.1:5057')
out=Path('docs/screenshots');out.mkdir(parents=True,exist_ok=True)
checks=[]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True)
 page=browser.new_page(viewport={'width':1440,'height':1040},device_scale_factor=1)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(base);expect(page.locator('.product-card')).to_have_count(20);checks.append('Catalog: 20 products loaded from backend')
 page.screenshot(path=str(out/'market-desktop.png'),full_page=True)
 page.get_by_role('button',name='Bakery',exact=True).click();expect(page.locator('.product-card')).to_have_count(2)
 page.get_by_role('button',name='All essentials').click();page.get_by_role('searchbox').fill('milk');expect(page.locator('.product-card')).to_have_count(1);checks.append('Categories and case-insensitive live search')
 page.get_by_role('searchbox').fill('zzzz');expect(page.get_by_text('No products found. Try another search.')).to_be_visible();page.get_by_role('searchbox').fill('')
 page.get_by_role('button',name='Add Farm fresh bananas',exact=True).click();expect(page.locator('#cart-count')).to_have_text('1');page.reload();expect(page.locator('#cart-count')).to_have_text('1');checks.append('Guest basket survives reload')
 page.locator('#cart-btn').click();page.get_by_role('button',name='Sign in to checkout').click();page.get_by_role('button',name='New here? Create an account').click()
 email=f'e2e{time.time_ns()}@example.test'
 page.get_by_label('Your name').fill('Demo Shopper');page.get_by_label('Email address').fill(email);page.get_by_label('Password · 10 characters minimum').fill('Browser-demo-2026');page.get_by_role('button',name='Create account',exact=True).click()
 expect(page.get_by_label('Demo delivery address')).to_be_visible();checks.append('Registration, session cookie and guest-to-account basket merge')
 denied=page.evaluate("async()=>{let r=await fetch('/api/admin');return r.status}");assert denied==403;checks.append('Customer admin API access refused (403)')
 page.get_by_label('Demo delivery address').fill('123 Example Street, Demo City');page.get_by_role('button',name='Place demo order',exact=False).click()
 expect(page.locator('.order-card')).to_have_count(1);expect(page.locator('.order-card')).to_contain_text('Farm fresh bananas');expect(page.locator('#cart-count')).to_have_text('0');checks.append('Demo order placed; server-priced snapshot displayed; basket cleared')
 page.locator('#close-dialog').click();page.reload();page.locator('#orders-btn').click();expect(page.locator('.order-card')).to_have_count(1);checks.append('Order history and authenticated session survive page reload')
 page.locator('#close-dialog').click();page.locator('#account-btn').click();page.get_by_role('button',name='Sign out',exact=True).click();expect(page.locator('#account-btn')).to_have_text('Sign in')
 page.locator('#account-btn').click();page.get_by_label('Email address').fill(email);page.get_by_label('Password · 10 characters minimum').fill('Browser-demo-2026');page.get_by_role('button',name='Sign in',exact=True).last.click();expect(page.locator('#dialog')).not_to_be_visible();checks.append('Logout and password login')
 page.locator('#account-btn').click();page.get_by_role('button',name='Sign out',exact=True).click();page.locator('#account-btn').click();page.get_by_label('Email address').fill('admin@example.test');page.get_by_label('Password · 10 characters minimum').fill('Admin-demo-2026');page.get_by_role('button',name='Sign in',exact=True).last.click();expect(page.locator('#admin-btn')).to_be_visible()
 page.locator('#admin-btn').click();expect(page.locator('.admin-item')).to_have_count(20)
 row=page.locator('.admin-item').first;row.get_by_label('Farm fresh bananas price in paise').fill('5200');row.get_by_label('Farm fresh bananas stock').fill('33');row.get_by_role('button',name='Save',exact=True).click();expect(page.locator('#toast')).to_have_text('Inventory saved.');checks.append('Admin inventory price and stock persisted through protected endpoint')
 page.get_by_role('button',name='Mark demo packed',exact=True).first.click();expect(page.locator('.admin-order').first).to_contain_text('Demo packed');checks.append('Admin advances demo order workflow')
 page.screenshot(path=str(out/'admin-desktop.png'))
 page.locator('#close-dialog').click();page.get_by_role('searchbox').fill('bananas');expect(page.locator('.product-card .price')).to_have_text('₹52.00');page.get_by_role('searchbox').fill('');checks.append('Storefront reflects admin update')
 page.set_viewport_size({'width':390,'height':844});page.reload();expect(page.locator('.product-card')).to_have_count(20)
 assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
 page.screenshot(path=str(out/'market-mobile.png'));page.locator('#cart-btn').click();assert page.locator('#dialog').bounding_box()['width']<=390;checks.append('390px mobile storefront and dialog fit without horizontal page overflow')
 # Stored untrusted strings must be text nodes, never markup.
 malicious=browser.new_page(viewport={'width':1000,'height':800})
 malicious.goto(base);expect(malicious.locator('.product-card')).to_have_count(20)
 attack="<img src=x onerror=alert(1)>"
 malicious.evaluate("""async ({attack,email})=>{let s=await (await fetch('/api/session')).json();const post=async(path,d)=>{let r=await fetch('/api'+path,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':s.csrf},body:JSON.stringify(d)});let v=await r.json();if(v.csrf)s.csrf=v.csrf;return v;};await post('/register',{name:attack,email,password:'Browser-demo-2026'});await fetch('/api/cart',{method:'PUT',headers:{'Content-Type':'application/json','X-CSRF-Token':s.csrf},body:JSON.stringify({items:[{product_id:1,quantity:1}]})});await post('/orders',{address:attack,request_key:'markup-safety-12345'});} """,{'attack':attack,'email':f'xss{time.time_ns()}@example.test'})
 malicious.reload();malicious.locator('#orders-btn').click();expect(malicious.locator('.order-card')).to_contain_text(attack);assert malicious.locator('img[src="x"]').count()==0;checks.append('Stored markup in name/address rendered as text, not executable HTML')
 malicious.close()
 assert not errors,errors;checks.append('No uncaught browser JavaScript errors')
 browser.close()
Path('docs/browser-results.json').write_text(json.dumps({'checks':checks,'passed':len(checks),'page_errors':errors,'browser':'Chromium 140 / Playwright 1.55.0','simulation_only':True},indent=2))
print(json.dumps({'passed':len(checks),'checks':checks},indent=2))
