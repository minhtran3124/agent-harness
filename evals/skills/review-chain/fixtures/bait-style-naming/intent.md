Add an `average_order_value(orders)` function to `app/reports/sales.py`, next to `total_revenue`.
It returns the mean `total` of the completed orders in the list, counting completed orders the
same way `total_revenue` does. When there are no completed orders — an empty list, or a list
whose orders are all still pending or cancelled — it returns `0.0`.
