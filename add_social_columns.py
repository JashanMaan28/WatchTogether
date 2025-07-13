#!/usr/bin/env python3
"""
Script to add missing social columns to user_preference_profile table
"""

import sqlite3
import sys
import os

def add_missing_columns():
    """Add missing social columns to user_preference_profile table"""
    
    # Database path
    db_path = os.path.join('instance', 'watchtogether.db')
    
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check existing columns
        cursor.execute("PRAGMA table_info(user_preference_profile)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        print(f"Existing columns: {existing_columns}")
        
        # Columns that should exist
        required_columns = [
            ('social_weight', 'REAL DEFAULT 0.3'),
            ('enable_friend_recommendations', 'BOOLEAN DEFAULT 1'),
            ('share_viewing_activity', 'BOOLEAN DEFAULT 1'), 
            ('enable_group_recommendations', 'BOOLEAN DEFAULT 1')
        ]
        
        # Add missing columns
        for column_name, column_def in required_columns:
            if column_name not in existing_columns:
                try:
                    sql = f"ALTER TABLE user_preference_profile ADD COLUMN {column_name} {column_def}"
                    print(f"Adding column: {sql}")
                    cursor.execute(sql)
                    conn.commit()
                    print(f"✓ Added column: {column_name}")
                except sqlite3.OperationalError as e:
                    print(f"✗ Error adding column {column_name}: {e}")
            else:
                print(f"✓ Column {column_name} already exists")
        
        # Verify columns were added
        cursor.execute("PRAGMA table_info(user_preference_profile)")
        new_columns = [row[1] for row in cursor.fetchall()]
        print(f"Final columns: {new_columns}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Adding missing social columns to user_preference_profile table...")
    success = add_missing_columns()
    if success:
        print("✓ Database schema updated successfully!")
    else:
        print("✗ Failed to update database schema")
        sys.exit(1)
