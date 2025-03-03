# mydb.py
from tinydb import TinyDB, Query
from typing import Dict, Any, List
from passlib.context import CryptContext  # For password hashing

# Password hashing context (same as jwt_auth.py)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class MyDB:
    def __init__(self, db_path: str):
        """
        Initializes the MyDB class with the path to the TinyDB database file.
        """
        self.db = TinyDB(db_path)
        self.User = Query()

    def get_user(self, username: str) -> Dict[str, Any] | None:
        """
        Retrieves a user from the database based on the username.

        Args:
            username: The username of the user to retrieve.

        Returns:
            A dictionary containing the user data, or None if the user is not found.
        """
        result = self.db.search(self.User.username == username)
        if result:
            return result[0]  # Return the first match
        else:
            return None

    def insert_user(self, user_data: Dict[str, Any]):
        """Inserts a new user into the database.

        Args:
            user_data: A dictionary containing the user's data, including username and password.
        """
        self.db.insert(user_data)

    def update_user(self, username: str, updates: Dict[str, Any]):
        """Updates a user's information in the database.

        Args:
            username: The username of the user to update.
            updates: A dictionary containing the fields to update and their new values.
        """
        self.db.update(updates, self.User.username == username)

    def delete_user(self, username: str):
        """Deletes a user from the database.

        Args:
            username: The username of the user to delete.
        """
        self.db.remove(self.User.username == username)

    def all_users(self) -> List[Dict[str, Any]]:
      """Returns a list of all users in the database."""
      return self.db.all()

    def clear_db(self):
        """Clears all data from the database.  Use with caution!"""
        self.db.truncate()


if __name__ == '__main__':
    # Example Usage (for database writing/management)
    db = MyDB("workspace/db.json")  # Same path as in jwt_auth.py

    # Clear the database before running tests (CAREFUL!)
    # db.clear_db()

    # Create some users with hashed passwords
    users_to_create = [
        {"username": "testuser", "password": pwd_context.hash("adminpassword")},
        {"username": "user1", "password": pwd_context.hash("password123")},
        {"username": "user2", "password": pwd_context.hash("secure_pass")},
    ]

    for user_data in users_to_create:
        # Check if the user already exists to avoid duplicates
        if not db.get_user(user_data["username"]):
            db.insert_user(user_data)
            print(f"User {user_data['username']} created.")
        else:
            print(f"User {user_data['username']} already exists.")

    # Example of updating a user (e.g., setting an email)
    db.update_user("user1", {"email": "user1@example.com"})
    print("User1 email updated.")


    # Show all users
    all_users = db.all_users()
    print(f"All users in the database: {all_users}")

    #Demonstrate reading of user data:
    retrieved_user = db.get_user("admin")
    print(f"Retrieved admin user: {retrieved_user}")