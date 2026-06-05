#!/usr/bin/env python3
"""
Script to grant Super Admin privileges to a user by email.
"""

import sqlite3

DB_PATH = "social_learning.db"

def grant_super_admin(email):
    """Grant Super Admin role to user with specified email."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id, username, role FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ User not found with email: {email}")
            return False
        
        current_role = user['role']
        print(f"Found user: {user['username']} (ID: {user['id']}, Current role: {current_role})")
        
        # Update role to Super Admin
        cursor.execute("UPDATE users SET role = ? WHERE email = ?", ("Super Admin", email))
        conn.commit()
        
        print(f"✅ Successfully granted Super Admin privileges to {email}")
        
        # Verify the change
        cursor.execute("SELECT role FROM users WHERE email = ?", (email,))
        updated_user = cursor.fetchone()
        print(f"✅ Verified: {email} now has role: {updated_user['role']}")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    email = "adetola.coke@gmail.com"
    grant_super_admin(email)
