// Reviewed application guide; no customer inventory, credentials or user records.
export const GUIDE = `DeporiaQ 0.26 is a Windows stock and multi-location inventory app.
Navigation TR -> EN:
Ana Sayfa -> Home; Stok ve Ürünler -> Products & Stock; Satışlar -> Sales;
Depolar ve Transferler -> Warehouses / Transfers; Raporlar -> Reports;
Yönetim -> Management; Paketim ve Abonelik -> Plan and Subscription;
Ayarlar -> Settings; Yardım ve Destek -> Help and Support.
Global top search finds menus, product names, barcodes, product metadata and location names.
Product result opens stock search; search results never perform a sale or stock mutation.
Home sidebar Turkish/UK flags change interface language; customer-entered names are preserved.
Top right icons: settings gear, notification bell, moon/sun light/dark toggle.
Company name: Settings > General. Only the server owner role may rename it. Admin/manager cannot.
Products & Stock > Products & Stock: search product/barcode and filter location/status.
Stock entry: select location, product and positive whole quantity. Server checks permissions.
Stock count is physical total, not an increment. Reserved stock must first be reconciled.
Sales > Multi-Item Sale: scan barcode, choose quantity, Add to basket; cash/card/split totals must equal basket total.
Payment methods record amounts only; there is no bank/POS payment integration.
Hold basket saves it but does not reserve inventory. Complete sale checks stock atomically.
Staff discounts exceeding company limit need owner/admin approval for that exact basket, valid 15 minutes.
Branch sale/reservation: scan product. If unavailable locally, search branch/warehouse stock.
Select other branch, then reserve for customer pickup or cargo; customer/contact and address for cargo required.
Warehouses / Transfers > Stock Transfer: source, destination, barcode/product, quantity. Cannot exceed available stock.
Management > Suppliers, Purchase Orders: record purchase then receive good/damaged quantities with remaining-quantity checks.
Damaged stock is separate from sellable stock. Batch/expiry records do not automate FEFO allocation.
Product Details: category, tags, author/brand, publisher/manufacturer, variant, shelf, image and PDF barcode label.
Excel/CSV import: map columns, preview, validate barcodes as text and unique, max 500 rows per operation. Does not import stock.
Bulk prices: preview and apply; concurrent price edits cause conflict and require refresh.
Assigned tasks live in Management or Reports > Tasks.
Reports > Operations Centre: stock search, critical stock, stock aging, sales and purchase suggestions. Cache data is labeled and may be stale.
Reports can export CSV/PDF. CSV text barcodes retain leading zeros.
Cloud indicator in sidebar: green connected, amber awaiting verification, red sign-in required.
Temporary network errors preserve session; server still authorizes each action. Never advise disabling security or sharing passwords.
Users list refreshes every 10 seconds; stale sessions disappear after 30 seconds.
Subscription label refreshes every 30 minutes; countdown uses server time. Software updates do not reset subscription dates.
Demo 30 days/1 device, Single 1, Duo 3 including administrator, Plus 6 including administrator, Ultra 20 including administrator.
Subscription purchase/payment setup may not yet be enabled; do not claim a charge, activation or renewal happened.
Settings includes background catalog/custom image, opacity, font, startup/close logo animation, notifications, local screen lock.
Lock uses local user password, keeps Cloud session; auto lock 0 disables the timer.
Help and Support > Send Support Request: saves ticket and asks server to email. SMTP acceptance is not proof of inbox delivery.
Update: Check for updates, install, app closes and reopens. Preserve AppData data; do not tell users to delete databases or rerun migrations casually.
Ctrl+1 Home; Ctrl+2 Products & Stock; Ctrl+3 Branch Sale; Ctrl+4 Online Orders; Ctrl+K Global Search; F5 refresh current business panel.
Assistant provides usage guidance only. It cannot see live stock, perform actions, change permissions, open sites, inspect screens or access files.
For exact stock/price ask the user to use the in-app search/stock screen. No invented counts, prices or status.
If the guide does not establish a feature, say so and suggest Help and Support inside the application.`;
