<template name="CustomManufacturingOrderReport">
    <h1>Manufacturing Order: {{ record.name }}</h1>
    <p>Product: {{ record.product_id.name }}</p>
    <p>Quantity: {{ record.product_uom_qty }}</p>
    </template>