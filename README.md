# Ozi_Insta

A powerful Instagram account management tool built with Python and instagrapi.

## Features

- **Secure Multi-Account Management**
  - Add/remove multiple Instagram accounts
  - Encrypted session storage
  - Automatic session refresh

- **Relationship Analysis**
  - Complete follower/following analysis
  - Non-mutual follow detection
  - Detailed statistics and ratios

- **Smart Unfollowing**
  - Whitelist support for important accounts
  - Configurable delays between actions (1-3 seconds)
  - Daily unfollow limits (max 200/day)
  - Exclude verified and business accounts
  - Confirmation prompts for safety

- **User-Friendly CLI**
  - Interactive menus
  - Progress bars
  - Detailed logging
  - CSV export capabilities

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ozi_insta.git
cd ozi_insta
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the tool:
```bash
python main.py
```

### Main Menu Options

1. **Add Account** - Add a new Instagram account
2. **Remove Account** - Remove an existing account
3. **View Account Statistics** - See follower/following statistics
4. **Smart Unfollow** - Start the unfollowing process
5. **Manage Whitelist** - Add/remove accounts from whitelist
6. **Exit** - Close the application

## Safety Features

- Encrypted session storage
- Rate limiting compliance
- Random delays between actions
- Following list backup before unfollowing
- Confirmation prompts for important actions
- Emergency stop functionality

## Files

- `sessions.enc` - Encrypted session storage
- `whitelist.json` - Whitelist configuration
- `instagram_manager.log` - Activity log
- Backup CSVs - Created before unfollowing operations

## Requirements

- Python 3.8+
- Dependencies listed in requirements.txt

## License

MIT License

## Disclaimer

This tool is for educational purposes only. Use at your own risk and in compliance with Instagram's terms of service.
