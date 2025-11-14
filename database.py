"""
Database module for user management and usage tracking.
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "elliptic_bot.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize database tables."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id TEXT UNIQUE NOT NULL,
                telegram_username TEXT,
                is_admin BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                daily_limit INTEGER DEFAULT 10,
                monthly_limit INTEGER DEFAULT 300,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Usage tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                wallet_address TEXT NOT NULL,
                risk_score REAL,
                decision TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # API errors log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS error_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                error_type TEXT NOT NULL,
                error_message TEXT,
                wallet_address TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    # User Management
    def add_user(self, telegram_id: str, telegram_username: str = None, 
                 is_admin: bool = False, daily_limit: int = 10, 
                 monthly_limit: int = 300) -> bool:
        """Add a new user to the whitelist."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (telegram_id, telegram_username, is_admin, daily_limit, monthly_limit)
                VALUES (?, ?, ?, ?, ?)
            """, (telegram_id, telegram_username, is_admin, daily_limit, monthly_limit))
            conn.commit()
            conn.close()
            logger.info(f"Added user: {telegram_id} (@{telegram_username})")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"User {telegram_id} already exists")
            return False
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False
    
    def remove_user(self, telegram_id: str) -> bool:
        """Remove a user from the whitelist."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
            conn.commit()
            affected = cursor.rowcount
            conn.close()
            if affected > 0:
                logger.info(f"Removed user: {telegram_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing user: {e}")
            return False
    
    def get_user(self, telegram_id: str) -> Optional[Dict]:
        """Get user information."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                return dict(row)
            return None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def is_user_authorized(self, telegram_id: str) -> bool:
        """Check if user is authorized and active."""
        user = self.get_user(telegram_id)
        return user is not None and user['is_active']
    
    def is_user_admin(self, telegram_id: str) -> bool:
        """Check if user is an admin."""
        user = self.get_user(telegram_id)
        return user is not None and user['is_admin']
    
    def update_user_limits(self, telegram_id: str, daily_limit: int = None, 
                          monthly_limit: int = None) -> bool:
        """Update user's usage limits."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if daily_limit is not None:
                updates.append("daily_limit = ?")
                params.append(daily_limit)
            
            if monthly_limit is not None:
                updates.append("monthly_limit = ?")
                params.append(monthly_limit)
            
            if not updates:
                return False
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(telegram_id)
            
            query = f"UPDATE users SET {', '.join(updates)} WHERE telegram_id = ?"
            cursor.execute(query, params)
            conn.commit()
            affected = cursor.rowcount
            conn.close()
            
            if affected > 0:
                logger.info(f"Updated limits for user: {telegram_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating user limits: {e}")
            return False
    
    def toggle_user_status(self, telegram_id: str, is_active: bool) -> bool:
        """Activate or deactivate a user."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET is_active = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE telegram_id = ?
            """, (is_active, telegram_id))
            conn.commit()
            affected = cursor.rowcount
            conn.close()
            
            if affected > 0:
                status = "activated" if is_active else "deactivated"
                logger.info(f"User {telegram_id} {status}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error toggling user status: {e}")
            return False
    
    def get_all_users(self) -> List[Dict]:
        """Get all users."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    # Usage Tracking
    def log_usage(self, telegram_id: str, wallet_address: str, 
                  risk_score: float = None, decision: str = None) -> bool:
        """Log a wallet analysis request."""
        try:
            user = self.get_user(telegram_id)
            if not user:
                return False
            
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO usage_logs (user_id, wallet_address, risk_score, decision)
                VALUES (?, ?, ?, ?)
            """, (user['id'], wallet_address, risk_score, decision))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error logging usage: {e}")
            return False
    
    def get_usage_count(self, telegram_id: str, period: str = 'day') -> int:
        """Get usage count for a user in a specific period."""
        try:
            user = self.get_user(telegram_id)
            if not user:
                return 0
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if period == 'day':
                time_threshold = datetime.now() - timedelta(days=1)
            elif period == 'month':
                time_threshold = datetime.now() - timedelta(days=30)
            else:
                return 0
            
            cursor.execute("""
                SELECT COUNT(*) as count FROM usage_logs 
                WHERE user_id = ? AND timestamp >= ?
            """, (user['id'], time_threshold))
            
            result = cursor.fetchone()
            conn.close()
            return result['count'] if result else 0
        except Exception as e:
            logger.error(f"Error getting usage count: {e}")
            return 0
    
    def check_usage_limit(self, telegram_id: str) -> Tuple[bool, str, int, int]:
        """
        Check if user has exceeded usage limits.
        Returns: (can_use, message, remaining_daily, remaining_monthly)
        """
        user = self.get_user(telegram_id)
        if not user:
            return False, "User not authorized", 0, 0
        
        daily_usage = self.get_usage_count(telegram_id, 'day')
        monthly_usage = self.get_usage_count(telegram_id, 'month')
        
        daily_limit = user['daily_limit']
        monthly_limit = user['monthly_limit']
        
        remaining_daily = max(0, daily_limit - daily_usage)
        remaining_monthly = max(0, monthly_limit - monthly_usage)
        
        if daily_usage >= daily_limit:
            return False, f"Daily limit reached ({daily_limit} queries/day)", remaining_daily, remaining_monthly
        
        if monthly_usage >= monthly_limit:
            return False, f"Monthly limit reached ({monthly_limit} queries/month)", remaining_daily, remaining_monthly
        
        return True, "OK", remaining_daily, remaining_monthly
    
    def get_user_usage_stats(self, telegram_id: str) -> Dict:
        """Get detailed usage statistics for a user."""
        try:
            user = self.get_user(telegram_id)
            if not user:
                return {}
            
            daily_usage = self.get_usage_count(telegram_id, 'day')
            monthly_usage = self.get_usage_count(telegram_id, 'month')
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get total usage
            cursor.execute("""
                SELECT COUNT(*) as total FROM usage_logs WHERE user_id = ?
            """, (user['id'],))
            total_usage = cursor.fetchone()['total']
            
            # Get recent decisions
            cursor.execute("""
                SELECT decision, COUNT(*) as count 
                FROM usage_logs 
                WHERE user_id = ? AND timestamp >= datetime('now', '-30 days')
                GROUP BY decision
            """, (user['id'],))
            decisions = {row['decision']: row['count'] for row in cursor.fetchall()}
            
            conn.close()
            
            return {
                'telegram_id': telegram_id,
                'telegram_username': user['telegram_username'],
                'daily_usage': daily_usage,
                'daily_limit': user['daily_limit'],
                'monthly_usage': monthly_usage,
                'monthly_limit': user['monthly_limit'],
                'total_usage': total_usage,
                'decisions': decisions,
                'is_admin': user['is_admin'],
                'is_active': user['is_active']
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}
    
    def get_all_usage_stats(self) -> List[Dict]:
        """Get usage statistics for all users."""
        users = self.get_all_users()
        stats = []
        for user in users:
            user_stats = self.get_user_usage_stats(user['telegram_id'])
            if user_stats:
                stats.append(user_stats)
        return stats
    
    # Error Logging
    def log_error(self, telegram_id: str = None, error_type: str = None, 
                  error_message: str = None, wallet_address: str = None) -> bool:
        """Log an error."""
        try:
            user_id = None
            if telegram_id:
                user = self.get_user(telegram_id)
                if user:
                    user_id = user['id']
            
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO error_logs (user_id, error_type, error_message, wallet_address)
                VALUES (?, ?, ?, ?)
            """, (user_id, error_type, error_message, wallet_address))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error logging error: {e}")
            return False
    
    def get_recent_errors(self, limit: int = 50) -> List[Dict]:
        """Get recent errors."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.*, u.telegram_id, u.telegram_username 
                FROM error_logs e
                LEFT JOIN users u ON e.user_id = u.id
                ORDER BY e.timestamp DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting recent errors: {e}")
            return []
