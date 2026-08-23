from app.data.dummy_data import customers


def get_customer(customer_id: int):

    for customer in customers:

        if customer["customer_id"] == customer_id:
            return customer

    return None


def create_customer(name, phone, address):

    new_id = len(customers) + 1

    customer = {
        "customer_id": new_id,
        "name": name,
        "phone": phone,
        "address": address
    }

    customers.append(customer)

    return customer