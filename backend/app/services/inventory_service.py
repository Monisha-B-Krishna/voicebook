from app.data.dummy_data import inventory


def get_inventory_item(item_id: int):

    for item in inventory:

        if item["item_id"] == item_id:
            return item

    return None


def check_availability(item_id: int, quantity: int):

    item = get_inventory_item(item_id)

    if item is None:

        return {
            "available": False,
            "reason": "Inventory item not found"
        }

    if item["available_quantity"] < quantity:

        return {
            "available": False,
            "reason": "Insufficient inventory",
            "requested": quantity,
            "available": item["available_quantity"]
        }

    return {
        "available": True,
        "item": item
    }


def reserve_inventory(item_id: int, quantity: int):

    item = get_inventory_item(item_id)

    if item is None:
        raise ValueError("Inventory item not found")

    if item["available_quantity"] < quantity:
        raise ValueError("Insufficient inventory")

    item["available_quantity"] -= quantity

    return item


def return_inventory(item_id: int, quantity: int):

    item = get_inventory_item(item_id)

    if item is None:
        raise ValueError("Inventory item not found")

    item["available_quantity"] += quantity

    return item