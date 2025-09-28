from database import (
    SessionLocal,
    User,
    Device,
    Reading,
    get_password_hash,
    create_db_and_tables,
)
from datetime import datetime, timedelta, UTC
import os


def seed_database():
    if os.path.exists("weather.db"):
        os.remove("weather.db")

    # Create the database and tables
    create_db_and_tables()

    db = SessionLocal()

    # Check if data already exists
    if db.query(User).count() > 0:
        print("Database already seeded.")
        db.close()
        return

    # --- Create Users ---
    user1 = User(username="test", hashed_password=get_password_hash("test"))
    user2 = User(username="test2", hashed_password=get_password_hash("test2"))
    db.add_all([user1, user2])
    db.commit()

    # --- Create Devices ---
    device1 = Device(
        device_code="DEV001",
        name="London Weather Station",
        latitude=51.5074,
        longitude=-0.1278,
        owner=user1,
    )
    device2 = Device(
        device_code="DEV002",
        name="New York Weather Station",
        latitude=40.7128,
        longitude=-74.0060,
        owner=user1,
    )
    device3 = Device(
        device_code="DEV003",
        name="Tokyo Weather Station",
        latitude=35.6895,
        longitude=139.6917,
        owner=user2,
    )
    device4 = Device(
        device_code="DEV004",
        name="Chennai Station",
        latitude=12.896,
        longitude=80.224,
        owner=user1,
    )
    db.add_all([device1, device2, device3, device4])
    db.commit()

    # --- Create Readings ---
    for i in range(10):
        db.add(
            Reading(
                device=device1,
                temperature=20 + i * 0.5,
                pressure=1010 + i * 0.2,
                humidity=60 - i * 1.5,
                timestamp=datetime.now(UTC) - timedelta(hours=i),
            )
        )
    for i in range(5):
        db.add(
            Reading(
                device=device2,
                temperature=25 - i * 0.8,
                pressure=1005 + i * 0.5,
                humidity=70 + i * 1.2,
                timestamp=datetime.now(UTC) - timedelta(hours=i),
            )
        )

    db.commit()
    db.close()
    print("Database seeded successfully!")


if __name__ == "__main__":
    seed_database()
