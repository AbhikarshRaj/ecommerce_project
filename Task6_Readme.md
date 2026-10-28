# Task 6 — Operational Logs and Cart History

## Overview

This module implements operational activity logging for the MarketLane e-commerce application. It maintains a persistent record of product management and shopping cart operations using SQLite.

The implementation also provides an admin interface for viewing activity logs, filtering records, and navigating through the history.

## Features Implemented

### 1. Product Activity Logging

The system records the following administrative operations:

- `PRODUCT_CREATED` — When a new product is added.
- `PRODUCT_UPDATED` — When an existing product is modified.
- `PRODUCT_DELETED` — When a product is deleted.

Each event stores the event type, entity type, entity identifier, description, and timestamp.

### 2. Shopping Cart Activity Logging

The application records cart modifications, including:

- Adding products to the cart.
- Removing products from the cart.
- Increasing or decreasing product quantities.
- Undoing cart modifications.
- Redoing cart modifications.

The existing bounded-stack implementation supports cart undo and redo operations, while SQLite maintains a persistent record of the corresponding activities.

### 3. SQLite Activity Log Storage

A new `activity_logs` table stores operational events.

| Column | Description |
|---|---|
| `id` | Unique activity identifier |
| `event_type` | Type of operation |
| `entity_type` | Product or cart |
| `entity_id` | Associated entity identifier |
| `details` | Description of the activity |
| `created_at` | Event timestamp |

### 4. Admin Activity Logs Page

A dedicated admin page is available at:

`/admin/activity`

The page provides:

- Activity history displayed in a table.
- Filtering by event type and entity type.
- Pagination with 20 records per page.
- Direct navigation from the admin dashboard.
- Access restricted to authenticated administrators.

### 5. Automatic Log Retention

A log cleanup function removes activity records older than 90 days.

The cleanup runs during Flask application initialization, after the database has been initialized.

The retention period can be configured through the cleanup function.

## Files Modified or Added

| File | Contribution |
|---|---|
| `app/activity.py` | Event recording and log cleanup functions |
| `app/database.py` | Activity logs database schema |
| `app/admin.py` | Product activity logging and admin logs route |
| `app/cart.py` | Shopping cart activity logging |
| `app/__init__.py` | Automatic log cleanup initialization |
| `app/templates/admin_activity.html` | Admin activity logs interface |
| `app/templates/admin_catalog.html` | Activity Logs navigation button |

## Testing and Verification

The following operations were tested:

- Product creation, modification, and deletion logging.
- Cart addition, removal, undo, and redo logging.
- Storage and retrieval of activity records from SQLite.
- Display of activity records on the admin page.
- Product activity filtering.
- Automatic deletion of a temporary outdated log record.
- Preservation of existing activity records after cleanup.

The retention test confirmed that the temporary outdated record was removed, while 13 activity records remained in the database.

## Conclusion

Task 6 introduces persistent operational logging and an administrative activity history interface into MarketLane.

The implementation improves the traceability of product and cart operations while maintaining compatibility with the existing Flask application, SQLite database, and bounded-stack cart functionality.