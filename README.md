# Elliptic Telegram Bot - Enhanced Edition

A secure Telegram bot that analyzes cryptocurrency wallet addresses for risk assessment using Elliptic's API. Features user access control, usage limits, comprehensive error handling, and a web-based admin dashboard.

## Features

### Security & Access Control
- **User Whitelist**: Only authorized Telegram users can access the bot
- **Admin System**: Designated admins can manage users via bot commands
- **Role-Based Access**: Separate permissions for admins and regular users

### Usage Management
- **Daily Limits**: Configurable per-user daily query limits (default: 10)
- **Monthly Limits**: Configurable per-user monthly query limits (default: 300)
- **Usage Tracking**: Complete audit trail of all wallet analyses
- **Real-time Quota Display**: Users can check remaining queries

### Risk Analysis
- **Elliptic API Integration**: Professional-grade wallet risk assessment
- **Configurable Rules**: Customizable risk thresholds and compliance rules
- **High-Risk Detection**: Automatic flagging of sanctioned entities, dark markets, ransomware, etc.
- **Geographic Risk**: Detection of transactions from sanctioned countries
- **Detailed Reporting**: Comprehensive analysis with exposure breakdowns

### Error Handling
- **Wallet Validation**: Format checking before API calls
- **Retry Logic**: Automatic retry with exponential backoff
- **Timeout Handling**: Graceful handling of slow API responses
- **Error Logging**: Complete error tracking for debugging
- **User-Friendly Messages**: Clear error explanations for users

### Admin Dashboard
- **Web Interface**: Modern dashboard for managing the bot
- **User Management**: Add, edit, remove users with custom limits
- **Usage Analytics**: Real-time statistics and historical data
- **Error Monitoring**: Track and analyze system errors
- **Responsive Design**: Works on desktop and mobile

## Project Structure

```
elliptic_bot_enhanced/
├── bot.py                  # Main Telegram bot application
├── config.py               # Configuration management
├── database.py             # SQLite database operations
├── elliptic_client.py      # Elliptic API client with retry logic
├── validators.py           # Input validation functions
├── Category_ID.csv         # Risk category mappings
├── requirements.txt        # Python dependencies
├── Procfile               # Railway deployment config
├── .env.example           # Environment variables template
├── .gitignore             # Git ignore rules
└── README.md              # This file
```

## Installation

### Prerequisites
- Python 3.9 or higher
- Elliptic API credentials
- Telegram Bot Token (from @BotFather)

### Local Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd elliptic_bot_enhanced
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Set up admin user**
   Edit `.env` and set `ADMIN_TELEGRAM_ID` to your Telegram username (e.g., `jcmosquera`)

6. **Run the bot**
   ```bash
   python bot.py
   ```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ELLIPTIC_API_KEY` | Your Elliptic API key | Required |
| `ELLIPTIC_API_SECRET` | Your Elliptic API secret | Required |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from @BotFather | Required |
| `ADMIN_TELEGRAM_ID` | Initial admin Telegram username/ID | Required |
| `DATABASE_PATH` | Path to SQLite database file | `elliptic_bot.db` |
| `DEFAULT_DAILY_LIMIT` | Default daily query limit | `10` |
| `DEFAULT_MONTHLY_LIMIT` | Default monthly query limit | `300` |
| `RISK_SCORE_THRESHOLD` | Risk score rejection threshold | `5.0` |
| `MAX_HOP_DISTANCE` | Maximum hops for high-risk categories | `3` |
| `LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | `INFO` |

### Risk Analysis Rules

The bot applies the following compliance rules:

1. **Risk Score**: Rejects wallets with risk score ≥ 5
2. **High-Risk Categories**: Rejects if connected to dark markets, ransomware, terrorist organizations, etc. within 3 hops
3. **Sanctioned Countries**: Rejects if connected to Iran, North Korea, Russia, etc. within 3 hops
4. **Gambling**: Special rules for gambling exposure (≤2 hops OR 3 hops with >3% contribution)

## Usage

### User Commands

| Command | Description |
|---------|-------------|
| `/start` | Show welcome message and available commands |
| `/help` | Display help information |
| `/stats` | View your usage statistics |
| `/limits` | Check remaining daily/monthly queries |

### Admin Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/adduser <username>` | Add user to whitelist | `/adduser johndoe` |
| `/removeuser <username>` | Remove user from whitelist | `/removeuser johndoe` |
| `/setlimit <username> <daily> <monthly>` | Set user limits | `/setlimit johndoe 20 500` |
| `/listusers` | List all authorized users | `/listusers` |
| `/usage` | View usage statistics for all users | `/usage` |

### Analyzing Wallets

Simply send any cryptocurrency wallet address to the bot:

```
1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
```

The bot will return:
- Risk score
- Approval/rejection decision
- Financial summary (inflow/outflow/balance)
- Exposure details
- Remaining query quota

## Deployment

### Railway Deployment

1. **Create Railway account** at [railway.app](https://railway.app)

2. **Create new project** from GitHub repository

3. **Set environment variables** in Railway dashboard:
   - `ELLIPTIC_API_KEY`
   - `ELLIPTIC_API_SECRET`
   - `TELEGRAM_BOT_TOKEN`
   - `ADMIN_TELEGRAM_ID`

4. **Deploy**: Railway will automatically detect the Procfile and deploy

### Heroku Deployment

1. **Create Heroku app**
   ```bash
   heroku create your-app-name
   ```

2. **Set environment variables**
   ```bash
   heroku config:set ELLIPTIC_API_KEY=your_key
   heroku config:set ELLIPTIC_API_SECRET=your_secret
   heroku config:set TELEGRAM_BOT_TOKEN=your_token
   heroku config:set ADMIN_TELEGRAM_ID=your_username
   ```

3. **Deploy**
   ```bash
   git push heroku main
   ```

4. **Scale worker**
   ```bash
   heroku ps:scale worker=1
   ```

## Admin Dashboard

A separate web dashboard is available for managing the bot. See the `elliptic_dashboard` project for:

- Visual user management interface
- Usage analytics and charts
- Error log monitoring
- Real-time statistics

## Database Schema

### Users Table
- `id`: Primary key
- `telegram_id`: Telegram user ID/username (unique)
- `telegram_username`: Display name
- `is_admin`: Admin flag
- `is_active`: Active status
- `daily_limit`: Daily query limit
- `monthly_limit`: Monthly query limit
- `created_at`: Registration timestamp
- `updated_at`: Last update timestamp

### Usage Logs Table
- `id`: Primary key
- `user_id`: Foreign key to users
- `wallet_address`: Analyzed wallet
- `risk_score`: Elliptic risk score
- `decision`: Approval/rejection decision
- `timestamp`: Analysis timestamp

### Error Logs Table
- `id`: Primary key
- `user_id`: Foreign key to users (nullable)
- `error_type`: Error category
- `error_message`: Error details
- `wallet_address`: Related wallet (nullable)
- `timestamp`: Error timestamp

## Troubleshooting

### Bot not responding
- Check that the bot is running (`python bot.py`)
- Verify `TELEGRAM_BOT_TOKEN` is correct
- Ensure you're authorized (check with admin)

### API errors
- Verify Elliptic API credentials
- Check API quota limits
- Review error logs in database

### Database errors
- Ensure write permissions for database file
- Check disk space
- Verify SQLite installation

## Security Best Practices

1. **Never commit `.env` file** - Use `.env.example` as template
2. **Rotate API keys regularly** - Update credentials periodically
3. **Monitor error logs** - Watch for suspicious activity
4. **Limit admin access** - Only trusted users should be admins
5. **Use HTTPS** - For dashboard deployment
6. **Regular backups** - Backup database regularly

## Support

For issues or questions:
1. Check error logs in database
2. Review Railway/Heroku logs
3. Verify environment variables
4. Contact bot administrator

## License

This project is proprietary. All rights reserved.

## Credits

- **Elliptic**: Blockchain analytics API
- **python-telegram-bot**: Telegram Bot API wrapper
- **Railway**: Deployment platform
