"""
Enhanced Elliptic Telegram Bot with user management and usage limits.
"""
import logging
import pytz
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    CallbackContext
)

import config
from database import Database
from elliptic_client import EllipticClient
from validators import validate_wallet_address, validate_telegram_username, validate_limit

# Set up logging
logging.basicConfig(
    format=config.LOG_FORMAT,
    level=getattr(logging, config.LOG_LEVEL)
)
logger = logging.getLogger(__name__)

# Initialize database and API client
db = Database(config.DATABASE_PATH)
elliptic = EllipticClient()

# Initialize admin user
def init_admin():
    """Initialize the default admin user."""
    admin_id = config.ADMIN_TELEGRAM_ID
    if not db.get_user(admin_id):
        db.add_user(
            telegram_id=admin_id,
            telegram_username=admin_id,
            is_admin=True,
            daily_limit=999,  # High limit for admin
            monthly_limit=9999
        )
        logger.info(f"Initialized admin user: {admin_id}")

init_admin()

# Helper Functions
def get_user_id(update: Update) -> str:
    """Get user's Telegram ID or username."""
    user = update.effective_user
    return user.username if user.username else str(user.id)

def is_authorized(telegram_id: str) -> bool:
    """Check if user is authorized."""
    return db.is_user_authorized(telegram_id)

def is_admin(telegram_id: str) -> bool:
    """Check if user is admin."""
    return db.is_user_admin(telegram_id)

# Command Handlers
async def start(update: Update, context: CallbackContext):
    """Handle /start command."""
    telegram_id = get_user_id(update)
    user = update.effective_user
    
    welcome_message = f"""
🤖 **Welcome to Elliptic Wallet Analysis Bot!**

Hello {user.first_name}! 

This bot analyzes cryptocurrency wallet addresses for risk assessment using Elliptic's API.

**How to use:**
Simply send a wallet address to analyze it.

**Available commands:**
/start - Show this welcome message
/help - Get help and usage information
/stats - View your usage statistics
/limits - Check your remaining queries

"""
    
    if is_admin(telegram_id):
        welcome_message += """
**Admin commands:**
/adduser <username> - Add user to whitelist
/removeuser <username> - Remove user from whitelist
/setlimit <username> <daily> <monthly> - Set user limits
/listusers - List all users
/usage - View all users' usage statistics

"""
    
    if not is_authorized(telegram_id):
        welcome_message += """
⚠️ **You are not authorized to use this bot.**
Please contact the administrator to request access.
"""
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def help_command(update: Update, context: CallbackContext):
    """Handle /help command."""
    help_text = """
📖 **Help - How to Use This Bot**

**Analyzing Wallets:**
Simply send any cryptocurrency wallet address (Bitcoin, Ethereum, etc.) and the bot will analyze it for risk.

**Understanding Results:**
• **Risk Score**: Overall risk level (0-10)
• **Decision**: Approved or Rejected based on compliance rules
• **Inflow/Outflow**: Transaction volumes in USD
• **Balance**: Current wallet balance

**Rejection Reasons:**
The bot may reject wallets due to:
• High risk score (≥5)
• Connection to high-risk categories (ransomware, dark markets, etc.)
• Links to sanctioned countries
• Gambling exposure within 2-3 hops

**Usage Limits:**
Each user has daily and monthly query limits. Use /limits to check your remaining queries.

**Need Help?**
Contact the bot administrator if you need assistance or higher limits.
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def stats_command(update: Update, context: CallbackContext):
    """Handle /stats command - show user's usage statistics."""
    telegram_id = get_user_id(update)
    
    if not is_authorized(telegram_id):
        await update.message.reply_text("⚠️ You are not authorized to use this bot.")
        return
    
    stats = db.get_user_usage_stats(telegram_id)
    
    if not stats:
        await update.message.reply_text("❌ Unable to retrieve statistics.")
        return
    
    decisions = stats.get('decisions', {})
    approved = decisions.get('Approved', 0) + sum(v for k, v in decisions.items() if k and k.startswith('Approved'))
    rejected = sum(v for k, v in decisions.items() if k and k.startswith('Rejected'))
    
    stats_message = f"""
📊 **Your Usage Statistics**

**User:** @{stats['telegram_username']}
**Status:** {'🔑 Admin' if stats['is_admin'] else '✅ Active' if stats['is_active'] else '❌ Inactive'}

**Usage:**
• Daily: {stats['daily_usage']}/{stats['daily_limit']} queries
• Monthly: {stats['monthly_usage']}/{stats['monthly_limit']} queries
• Total (All-time): {stats['total_usage']} queries

**Last 30 Days:**
• ✅ Approved: {approved}
• ❌ Rejected: {rejected}
"""
    
    await update.message.reply_text(stats_message, parse_mode='Markdown')

async def limits_command(update: Update, context: CallbackContext):
    """Handle /limits command - show remaining queries."""
    telegram_id = get_user_id(update)
    
    if not is_authorized(telegram_id):
        await update.message.reply_text("⚠️ You are not authorized to use this bot.")
        return
    
    can_use, message, remaining_daily, remaining_monthly = db.check_usage_limit(telegram_id)
    
    limits_message = f"""
🔢 **Your Remaining Queries**

**Daily:** {remaining_daily} queries remaining
**Monthly:** {remaining_monthly} queries remaining

{'✅ You can continue using the bot.' if can_use else '⚠️ ' + message}
"""
    
    await update.message.reply_text(limits_message, parse_mode='Markdown')

# Admin Commands
async def adduser_command(update: Update, context: CallbackContext):
    """Handle /adduser command - add user to whitelist (admin only)."""
    telegram_id = get_user_id(update)
    
    if not is_admin(telegram_id):
        await update.message.reply_text("⚠️ This command is only available to administrators.")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "Usage: /adduser <username>\nExample: /adduser johndoe"
        )
        return
    
    new_user = context.args[0].lstrip('@')
    
    is_valid, error_msg = validate_telegram_username(new_user)
    if not is_valid:
        await update.message.reply_text(f"❌ {error_msg}")
        return
    
    success = db.add_user(
        telegram_id=new_user,
        telegram_username=new_user,
        daily_limit=config.DEFAULT_DAILY_LIMIT,
        monthly_limit=config.DEFAULT_MONTHLY_LIMIT
    )
    
    if success:
        await update.message.reply_text(
            f"✅ User @{new_user} added successfully!\n"
            f"Daily limit: {config.DEFAULT_DAILY_LIMIT}\n"
            f"Monthly limit: {config.DEFAULT_MONTHLY_LIMIT}"
        )
        logger.info(f"Admin {telegram_id} added user @{new_user}")
    else:
        await update.message.reply_text(f"❌ User @{new_user} already exists or could not be added.")

async def removeuser_command(update: Update, context: CallbackContext):
    """Handle /removeuser command - remove user from whitelist (admin only)."""
    telegram_id = get_user_id(update)
    
    if not is_admin(telegram_id):
        await update.message.reply_text("⚠️ This command is only available to administrators.")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "Usage: /removeuser <username>\nExample: /removeuser johndoe"
        )
        return
    
    user_to_remove = context.args[0].lstrip('@')
    
    # Prevent removing admin
    if db.is_user_admin(user_to_remove):
        await update.message.reply_text("❌ Cannot remove an admin user.")
        return
    
    success = db.remove_user(user_to_remove)
    
    if success:
        await update.message.reply_text(f"✅ User @{user_to_remove} removed successfully!")
        logger.info(f"Admin {telegram_id} removed user @{user_to_remove}")
    else:
        await update.message.reply_text(f"❌ User @{user_to_remove} not found.")

async def setlimit_command(update: Update, context: CallbackContext):
    """Handle /setlimit command - set user limits (admin only)."""
    telegram_id = get_user_id(update)
    
    if not is_admin(telegram_id):
        await update.message.reply_text("⚠️ This command is only available to administrators.")
        return
    
    if len(context.args) < 3:
        await update.message.reply_text(
            "Usage: /setlimit <username> <daily_limit> <monthly_limit>\n"
            "Example: /setlimit johndoe 20 500"
        )
        return
    
    username = context.args[0].lstrip('@')
    
    try:
        daily_limit = int(context.args[1])
        monthly_limit = int(context.args[2])
    except ValueError:
        await update.message.reply_text("❌ Limits must be valid numbers.")
        return
    
    is_valid_daily, error_msg = validate_limit(daily_limit)
    if not is_valid_daily:
        await update.message.reply_text(f"❌ Daily limit error: {error_msg}")
        return
    
    is_valid_monthly, error_msg = validate_limit(monthly_limit)
    if not is_valid_monthly:
        await update.message.reply_text(f"❌ Monthly limit error: {error_msg}")
        return
    
    success = db.update_user_limits(username, daily_limit, monthly_limit)
    
    if success:
        await update.message.reply_text(
            f"✅ Limits updated for @{username}!\n"
            f"Daily: {daily_limit}\n"
            f"Monthly: {monthly_limit}"
        )
        logger.info(f"Admin {telegram_id} updated limits for @{username}")
    else:
        await update.message.reply_text(f"❌ User @{username} not found.")

async def listusers_command(update: Update, context: CallbackContext):
    """Handle /listusers command - list all users (admin only)."""
    telegram_id = get_user_id(update)
    
    if not is_admin(telegram_id):
        await update.message.reply_text("⚠️ This command is only available to administrators.")
        return
    
    users = db.get_all_users()
    
    if not users:
        await update.message.reply_text("No users found.")
        return
    
    user_list = "👥 **All Users:**\n\n"
    for user in users:
        status = "🔑 Admin" if user['is_admin'] else ("✅ Active" if user['is_active'] else "❌ Inactive")
        user_list += f"@{user['telegram_username']} - {status}\n"
        user_list += f"  Limits: {user['daily_limit']}/day, {user['monthly_limit']}/month\n\n"
    
    await update.message.reply_text(user_list, parse_mode='Markdown')

async def usage_command(update: Update, context: CallbackContext):
    """Handle /usage command - view all users' usage (admin only)."""
    telegram_id = get_user_id(update)
    
    if not is_admin(telegram_id):
        await update.message.reply_text("⚠️ This command is only available to administrators.")
        return
    
    all_stats = db.get_all_usage_stats()
    
    if not all_stats:
        await update.message.reply_text("No usage data found.")
        return
    
    usage_report = "📈 **Usage Report (All Users):**\n\n"
    for stats in all_stats:
        usage_report += f"@{stats['telegram_username']}\n"
        usage_report += f"  Daily: {stats['daily_usage']}/{stats['daily_limit']}\n"
        usage_report += f"  Monthly: {stats['monthly_usage']}/{stats['monthly_limit']}\n"
        usage_report += f"  Total: {stats['total_usage']}\n\n"
    
    await update.message.reply_text(usage_report, parse_mode='Markdown')

# Wallet Analysis Handler
async def analyze_wallet(update: Update, context: CallbackContext):
    """Analyze a wallet address received from Telegram."""
    telegram_id = get_user_id(update)
    user = update.effective_user
    wallet_address = update.message.text.strip()
    
    # Check authorization
    if not is_authorized(telegram_id):
        await update.message.reply_text(
            "⚠️ **Access Denied**\n\n"
            "You are not authorized to use this bot. "
            "Please contact the administrator to request access.",
            parse_mode='Markdown'
        )
        return
    
    # Validate wallet address
    is_valid, error_msg = validate_wallet_address(wallet_address)
    if not is_valid:
        await update.message.reply_text(f"❌ {error_msg}")
        db.log_error(telegram_id, "VALIDATION_ERROR", error_msg, wallet_address)
        return
    
    # Check usage limits
    can_use, limit_msg, remaining_daily, remaining_monthly = db.check_usage_limit(telegram_id)
    if not can_use:
        await update.message.reply_text(
            f"⚠️ **Usage Limit Reached**\n\n{limit_msg}\n\n"
            f"Remaining daily: {remaining_daily}\n"
            f"Remaining monthly: {remaining_monthly}",
            parse_mode='Markdown'
        )
        return
    
    # Send "analyzing" message
    analyzing_msg = await update.message.reply_text("🔍 Analyzing wallet address...")
    
    # Call Elliptic API
    success, response_data, error_message = elliptic.analyze_wallet(wallet_address)
    
    if not success:
        await analyzing_msg.edit_text(
            f"❌ **Analysis Failed**\n\n{error_message}\n\n"
            "Please try again later or contact support if the issue persists.",
            parse_mode='Markdown'
        )
        db.log_error(telegram_id, "API_ERROR", error_message, wallet_address)
        return
    
    # Apply compliance rules
    decision, details = elliptic.apply_compliance_rules(response_data)
    risk_score = details.get('risk_score', 'N/A')
    
    # Log usage
    db.log_usage(telegram_id, wallet_address, risk_score, decision)
    
    # Get wallet financial info
    inflow = response_data.get("blockchain_info", {}).get("cluster", {}).get("inflow_value", {}).get("usd", 0)
    outflow = response_data.get("blockchain_info", {}).get("cluster", {}).get("outflow_value", {}).get("usd", 0)
    balance = inflow - outflow
    formatted_time = datetime.now(pytz.timezone('US/Eastern')).strftime("%B %d, %Y, %I:%M %p ET")
    
    # Format triggered rules
    triggered_rules_text = ""
    for risk_type, rules in details.get('triggered_rules', {}).items():
        if rules:
            triggered_rules_text += f"\n**{risk_type} Exposures:**\n"
            for rule in rules[:5]:  # Limit to top 5
                triggered_rules_text += f"  • {rule['category']} ({rule['hops']} hops, {rule['contribution']}%)\n"
    
    # Build response message
    result_message = f"""
🔍 **Wallet Risk Analysis**

**Address:** `{wallet_address[:20]}...`
**Risk Score:** {risk_score}
**Decision:** {"✅ " if decision == "Approved" else "❌ "}{decision}

💰 **Financial Summary:**
• Inflow: ${inflow:,.2f}
• Outflow: ${outflow:,.2f}
• Balance: ${balance:,.2f}

{triggered_rules_text}

🕒 **Analyzed:** {formatted_time}
📊 **Remaining Queries:** {remaining_daily - 1} daily, {remaining_monthly - 1} monthly
"""
    
    await analyzing_msg.edit_text(result_message, parse_mode='Markdown')
    logger.info(f"User {telegram_id} analyzed wallet: {wallet_address[:10]}... - {decision}")

def main():
    """Start the Telegram bot."""
    logger.info("Starting Elliptic Telegram Bot...")
    
    application = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("limits", limits_command))
    
    # Admin command handlers
    application.add_handler(CommandHandler("adduser", adduser_command))
    application.add_handler(CommandHandler("removeuser", removeuser_command))
    application.add_handler(CommandHandler("setlimit", setlimit_command))
    application.add_handler(CommandHandler("listusers", listusers_command))
    application.add_handler(CommandHandler("usage", usage_command))
    
    # Message handler for wallet analysis
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze_wallet))
    
    logger.info("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
