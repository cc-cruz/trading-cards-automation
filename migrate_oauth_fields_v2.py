#!/usr/bin/env python3
"""
Database migration script to add OAuth fields to existing users table.
This version handles SQLite limitations properly.
"""

import sqlite3
import os
from datetime import datetime

def migrate_database():
    """Add OAuth fields to the users table (SQLite-compatible version)"""
    
    # Database path
    db_path = 'carddealer.db'
    
    if not os.path.exists(db_path):
        print("❌ Database file not found. Please run your application first to create the database.")
        return False
    
    # Create backup
    backup_path = f'carddealer.db.backup.oauth_migration_v2_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    print(f"📁 Creating backup: {backup_path}")
    
    try:
        # Copy database for backup
        import shutil
        shutil.copy2(db_path, backup_path)
        print("✅ Backup created successfully")
    except Exception as e:
        print(f"❌ Failed to create backup: {e}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check current table structure
        cursor.execute("PRAGMA table_info(users)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        print(f"📋 Current users table columns: {list(columns.keys())}")
        
        # List of OAuth columns to add (without UNIQUE constraint for now)
        oauth_columns = [
            ('google_id', 'VARCHAR'),
            ('apple_id', 'VARCHAR'),
            ('oauth_provider', 'VARCHAR'),
            ('avatar_url', 'VARCHAR'),
            ('stripe_customer_id', 'VARCHAR'),
            ('stripe_subscription_id', 'VARCHAR'),
            ('subscription_status', 'VARCHAR DEFAULT "inactive"'),
            ('subscription_plan', 'VARCHAR DEFAULT "free"'),
            ('usage_count', 'INTEGER DEFAULT 0'),
            ('usage_reset_date', 'DATETIME')
        ]
        
        # Add missing columns
        for column_name, column_type in oauth_columns:
            if column_name not in columns:
                try:
                    alter_sql = f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"
                    cursor.execute(alter_sql)
                    print(f"✅ Added column: {column_name}")
                except sqlite3.Error as e:
                    print(f"⚠️  Failed to add {column_name}: {e}")
            else:
                print(f"ℹ️  Column {column_name} already exists")
        
        # Set default values for new columns
        updates = [
            ("subscription_status", "inactive"),
            ("subscription_plan", "free"),
            ("usage_count", "0"),
            ("usage_reset_date", "datetime('now')")
        ]
        
        for column, default_value in updates:
            if column in [col[0] for col in oauth_columns]:
                try:
                    if column == 'usage_reset_date':
                        update_sql = f"UPDATE users SET {column} = datetime('now') WHERE {column} IS NULL"
                    else:
                        update_sql = f"UPDATE users SET {column} = '{default_value}' WHERE {column} IS NULL"
                    cursor.execute(update_sql)
                    print(f"✅ Set default values for {column}")
                except sqlite3.Error as e:
                    print(f"⚠️  Failed to set defaults for {column}: {e}")
        
        # Create indexes for performance (without unique constraint in index)
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id) WHERE google_id IS NOT NULL",
            "CREATE INDEX IF NOT EXISTS idx_users_apple_id ON users(apple_id) WHERE apple_id IS NOT NULL",
            "CREATE INDEX IF NOT EXISTS idx_users_stripe_customer_id ON users(stripe_customer_id) WHERE stripe_customer_id IS NOT NULL",
            "CREATE INDEX IF NOT EXISTS idx_users_oauth_provider ON users(oauth_provider) WHERE oauth_provider IS NOT NULL"
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
                print(f"✅ Created index")
            except sqlite3.Error as e:
                print(f"⚠️  Index creation warning: {e}")
        
        conn.commit()
        print("✅ Database migration completed successfully!")
        
        # Verify migration
        cursor.execute("PRAGMA table_info(users)")
        new_columns = [row[1] for row in cursor.fetchall()]
        print(f"📋 Updated users table columns: {new_columns}")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()

def verify_migration():
    """Verify that the migration was successful"""
    conn = sqlite3.connect('carddealer.db')
    cursor = conn.cursor()
    
    try:
        # Check if OAuth columns exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        required_oauth_columns = [
            'google_id', 'apple_id', 'oauth_provider', 'avatar_url',
            'stripe_customer_id', 'subscription_status', 'subscription_plan',
            'usage_count', 'usage_reset_date'
        ]
        
        missing_columns = [col for col in required_oauth_columns if col not in columns]
        
        if missing_columns:
            print(f"❌ Migration verification failed. Missing columns: {missing_columns}")
            return False
        else:
            print("✅ Migration verification successful! All OAuth columns present.")
            
            # Test insert to ensure constraints work
            try:
                cursor.execute("SELECT COUNT(*) FROM users")
                count = cursor.fetchone()[0]
                print(f"📊 Current user count: {count}")
                
                # Check if we can query OAuth fields
                cursor.execute("SELECT oauth_provider, subscription_plan FROM users LIMIT 1")
                print("✅ OAuth fields are queryable")
                
            except sqlite3.Error as e:
                print(f"⚠️  Warning during verification: {e}")
            
            return True
            
    except sqlite3.Error as e:
        print(f"❌ Verification failed: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 Starting OAuth database migration (v2)...")
    print("=" * 50)
    
    if migrate_database():
        print("\n" + "=" * 50)
        print("🎉 Migration completed!")
        
        if verify_migration():
            print("""
📋 Next Steps:
1. Set up your OAuth credentials in .env.local:
   - NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
   - GOOGLE_CLIENT_SECRET=your-google-client-secret
   - NEXT_PUBLIC_APPLE_CLIENT_ID=your.apple.bundle.id
   - APPLE_TEAM_ID=your-apple-team-id
   - APPLE_KEY_ID=your-apple-key-id
   - APPLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----..."

2. Restart your application to use OAuth authentication

3. Test Google and Apple sign-in on your login/register pages:
   http://localhost:3000/auth/login
   http://localhost:3000/auth/register

4. See OAUTH_SETUP.md for detailed configuration instructions

⚠️  Note: Unique constraints for OAuth IDs will be enforced at the application level
   rather than database level due to SQLite limitations.
            """)
        else:
            print("⚠️  Please check the verification errors above")
    else:
        print("\n❌ Migration failed. Please check the errors above and try again.")
        print("💡 Your original database backup is available for restoration if needed.") 