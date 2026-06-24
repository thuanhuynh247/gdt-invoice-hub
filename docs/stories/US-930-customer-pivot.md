# US-930: Interactive Monthly Customer Pivot Table with Filters

## Objective
Provide the ability to aggregate, view, search, filter, and export a pivot table of sales invoices by customer (buyer) and month.

## Requirements
1. **Toggle Control**: Add a dropdown/selector in the partners pivot toolbar to switch between "Nhà cung cấp" (Supplier) and "Khách hàng" (Customer) views.
2. **API Integration**: Query `/api/invoices/customer-pivot` for Customer data, and `/api/invoices/supplier-pivot` for Supplier data.
3. **Dynamic Header**: Display "Tên khách hàng" when Customer is selected, and "Tên nhà cung cấp" when Supplier is selected.
4. **Excel Export**: Export utilizing `/api/invoices/customer-pivot/export` and `/api/invoices/supplier-pivot/export`.
5. **Filters & Search**: Implement text search (by name or Tax ID) and dynamic monthly values formatting matching MISA-style pivot presentation.
