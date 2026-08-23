from datetime import date

from app.database.connection import SessionLocal
from app.models.database_models import Customer, Inventory


def seed_database():

    db = SessionLocal()

    try:

        # ----------------------------------------------------
        # CUSTOMERS
        # ----------------------------------------------------

        customers = [
            Customer(
                name="Raju",
                phone="9876543210",
                address="Bengaluru"
            ),

            Customer(
                name="Suresh",
                phone="9876543211",
                address="Hosur"
            ),

            Customer(
                name="Priya",
                phone="9876543212",
                address="Electronic City"
            ),

            Customer(
                name="Manoj",
                phone="9876543213",
                address="Attibele"
            ),
        ]


        # ----------------------------------------------------
        # INVENTORY
        # ----------------------------------------------------

        inventory = [

            Inventory(
                item_name="Plastic Chair",
                category="Chairs",
                available_quantity=200,
                rental_price=10.00
            ),

            Inventory(
                item_name="Round Table",
                category="Tables",
                available_quantity=50,
                rental_price=150.00
            ),

            Inventory(
                item_name="Wedding Tent",
                category="Tents",
                available_quantity=10,
                rental_price=2500.00
            ),

            Inventory(
                item_name="LED Light",
                category="Lighting",
                available_quantity=100,
                rental_price=50.00
            ),

            Inventory(
                item_name="Plastic Mat",
                category="Flooring",
                available_quantity=100,
                rental_price=30.00
            ),
        ]


        db.add_all(customers)
        db.add_all(inventory)

        db.commit()

        print("VoiceBook dummy data inserted successfully.")


    except Exception as e:

        db.rollback()

        print("Error while inserting dummy data:")
        print(e)

        raise


    finally:

        db.close()


if __name__ == "__main__":

    seed_database()