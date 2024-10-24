 WITH inventory AS (
         SELECT pt_1.id AS product_id,
            COALESCE(sum(
                CASE
                    WHEN sl.usage::text = 'internal'::text THEN sq.quantity
                    ELSE 0::numeric
                END), 0::numeric) AS "In Inventory"
           FROM product_template pt_1
             LEFT JOIN product_product pp_1 ON pp_1.product_tmpl_id = pt_1.id
             LEFT JOIN stock_quant sq ON sq.product_id = pp_1.id
             LEFT JOIN stock_location sl ON sq.location_id = sl.id
          GROUP BY pt_1.id
        ), purchase_orders AS (
         SELECT pt_1.id AS product_id,
            COALESCE(sum(pol.product_qty - pol.qty_received) FILTER (WHERE (po_1.state::text = ANY (ARRAY['draft'::character varying, 'sent'::character varying, 'to approve'::character varying, 'purchase'::character varying, 'done'::character varying]::text[])) AND pol.product_qty > pol.qty_received AND po_1.state::text <> 'cancel'::text), 0::numeric) AS "On Order"
           FROM product_template pt_1
             LEFT JOIN product_product pp_1 ON pp_1.product_tmpl_id = pt_1.id
             LEFT JOIN purchase_order_line pol ON pol.product_id = pp_1.id
             LEFT JOIN purchase_order po_1 ON pol.order_id = po_1.id
          GROUP BY pt_1.id
        ), component_mo_month AS (
         SELECT pt_1.id AS product_id,
            pt_1.default_code AS product_code,
            pt_1.name ->> 'en_US'::text AS product_name,
            COALESCE(sum(
                CASE
                    WHEN to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) >= date_trunc('month'::text, CURRENT_DATE::timestamp with time zone)::date AND to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) <= (date_trunc('month'::text, CURRENT_DATE::timestamp with time zone) + '1 mon'::interval - '1 day'::interval)::date THEN sm.product_uom_qty
                    ELSE 0::numeric
                END), 0::numeric) AS month_1,
            COALESCE(sum(
                CASE
                    WHEN to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) >= (date_trunc('month'::text, CURRENT_DATE::timestamp with time zone) + '1 mon'::interval)::date AND to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) <= (date_trunc('month'::text, CURRENT_DATE::timestamp with time zone) + '2 mons'::interval - '1 day'::interval)::date THEN sm.product_uom_qty
                    ELSE 0::numeric
                END), 0::numeric) AS month_2,
            COALESCE(sum(
                CASE
                    WHEN to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) >= (date_trunc('month'::text, CURRENT_DATE::timestamp with time zone) + '2 mons'::interval)::date AND to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) <= (date_trunc('month'::text, CURRENT_DATE::timestamp with time zone) + '3 mons'::interval - '1 day'::interval)::date THEN sm.product_uom_qty
                    ELSE 0::numeric
                END), 0::numeric) AS month_3,
            COALESCE(sum(
                CASE
                    WHEN to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) >= (date_trunc('month'::text, CURRENT_DATE::timestamp with time zone) + '3 mons'::interval)::date AND to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) <= (date_trunc('month'::text, CURRENT_DATE::timestamp with time zone) + '4 mons'::interval - '1 day'::interval)::date THEN sm.product_uom_qty
                    ELSE 0::numeric
                END), 0::numeric) AS month_4,
            COALESCE(sum(
                CASE
                    WHEN to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) >= (date_trunc('month'::text, CURRENT_DATE::timestamp with time zone) + '4 mons'::interval)::date AND to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) <= (date_trunc('month'::text, CURRENT_DATE::timestamp with time zone) + '5 mons'::interval - '1 day'::interval)::date THEN sm.product_uom_qty
                    ELSE 0::numeric
                END), 0::numeric) AS month_5,
            COALESCE(sum(
                CASE
                    WHEN to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) >= (date_trunc('month'::text, CURRENT_DATE::timestamp with time zone) + '5 mons'::interval)::date AND to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) <= (date_trunc('month'::text, CURRENT_DATE::timestamp with time zone) + '6 mons'::interval - '1 day'::interval)::date THEN sm.product_uom_qty
                    ELSE 0::numeric
                END), 0::numeric) AS month_6,
            COALESCE(sum(
                CASE
                    WHEN to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) >= (date_trunc('month'::text, CURRENT_DATE::timestamp with time zone) + '6 mons'::interval)::date AND to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) <= (date_trunc('month'::text, CURRENT_DATE::timestamp with time zone) + '7 mons'::interval - '1 day'::interval)::date THEN sm.product_uom_qty
                    ELSE 0::numeric
                END), 0::numeric) AS month_7,
            COALESCE(sum(
                CASE
                    WHEN to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) >= (date_trunc('month'::text, CURRENT_DATE::timestamp with time zone) + '7 mons'::interval)::date AND to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) <= (date_trunc('month'::text, CURRENT_DATE::timestamp with time zone) + '8 mons'::interval - '1 day'::interval)::date THEN sm.product_uom_qty
                    ELSE 0::numeric
                END), 0::numeric) AS month_8
           FROM mrp_production mo
             JOIN stock_move sm ON mo.id = sm.raw_material_production_id
             JOIN product_product p ON sm.product_id = p.id
             JOIN product_template pt_1 ON p.product_tmpl_id = pt_1.id
          WHERE mo.state::text = 'confirmed'::text OR mo.state::text = 'progress'::text
          GROUP BY pt_1.id, pt_1.default_code, pt_1.name
        )
 SELECT cmmv.product_id AS id,
    pp.id AS product_id,
    cmmv.product_code AS component_code,
    cmmv.product_name AS component_name,
        CASE
            WHEN pt.type::text = 'product'::text THEN false
            ELSE true
        END AS is_storable,
    i."In Inventory" AS in_stock,
    po."On Order" AS on_order,
        CASE
            WHEN (EXISTS ( SELECT 1
               FROM mrp_bom mb
              WHERE mb.product_tmpl_id = pt.id)) THEN true
            ELSE false
        END AS has_bom,
    cmmv.month_1,
    cmmv.month_2,
    cmmv.month_3,
    cmmv.month_4,
    cmmv.month_5,
    cmmv.month_6,
    cmmv.month_7,
    cmmv.month_8
   FROM component_mo_month cmmv
     JOIN product_template pt ON cmmv.product_id = pt.id
     JOIN product_product pp ON pp.product_tmpl_id = pt.id
     LEFT JOIN inventory i ON i.product_id = cmmv.product_id
     LEFT JOIN purchase_orders po ON po.product_id = cmmv.product_id;