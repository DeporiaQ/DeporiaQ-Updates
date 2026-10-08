# Export review, 2026-10-08

Reviewed metadata: 206 original entries; supplemental 11 function definitions,
52 constraints, 7 row triggers and 27 indexes. No production modification performed.

Confirmed location types center/warehouse/branch, membership roles and subscription
status constraints match the candidate. Inventory conflict target matches the unique
key (company_id, location_id, product_id). Seven update triggers only set timestamps.

The original SECURITY DEFINER stock RPCs do not check subscription eligibility.
The first RPC checks membership without restricting viewers. The v2 RPCs do not
validate that product and locations belong to the given company. Individual UUID
foreign keys do not enforce these cross-company relationships.

006_legacy_rpc_security.sql adds checks before any legacy write/replay lookup,
restricts roles and paid time, validates product/location tenancy, and denies all
legacy stock calls for companies switched to the new reservation engine. Existing
paid, unmigrated clients retain their stock endpoint. No live change is implied.

Regression tests use the supplied legacy definitions (without customer data) and
relevant actual CHECK constraints. They cover migrated legacy calls, expired legacy
calls, viewer writes, foreign locations, valid paid legacy operations, and preservation
of a synthetic existing paid expiry during explicit package mapping. This is not a
full clone of production constraints/RLS/auth or a live customer-data reconciliation.

Remaining before release: aggregate inventory reconciliation and selected plan for
existing standard subscriptions; real payment provider, support delivery, trusted
trial enrollment and device clone protections. Current app is still candidate-only.
