from fastapi import Depends
from app.db.mongodb import get_database

def get_db():
    db = get_database()
    try:
        yield db
    finally:
        db.client.close()