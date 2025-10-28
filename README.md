# [TellySeerr]
[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Linter: Ruff](https://img.shields.io/badge/linter-ruff-brightgreen.svg)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful, all-in-one Telegram bot for managing your Jellyfin and Jellyseerr servers. It acts as a full-featured gateway for both you and your users, automating invites, handling media requests, and providing watch statistics.

## ✨ Core Features

### 👑 Admin Management
* **Easy User Invites:** Simply reply to a user in Telegram to invite them:
    * `/invite`: Creates a full, permanent Jellyfin/Jellyseerr account.
    * `/trial`: Creates a 7-day trial account.
    * `/vip`: Creates a 30-day VIP account.
* **User Management:**
    * `/deleteuser <username>`: Deletes a user from Jellyfin, Jellyseerr, and the bot's database.
    * `/listusers`: Shows a complete list of all users on your Jellyfin server.
* **Automatic Cleanup:** A background task runs daily to find and automatically delete expired trial/VIP users from all services.

### 👤 User Features
* **Self-Service Linking:** Users with existing accounts can link them to the bot with `/link <username> <password>`.
* **Personal Stats:** Users can run `/watch` to see their personal watch time and total items played from Jellyfin.

### 🎬 Media Requests (via Jellyseerr)
* **Search & Discover:**
    * `/request <name>`: Searches for new movies and shows.
    * `/discover`: Shows a browsable list of popular and trending media.
* **Full Request System:**
    * Users can submit media requests directly through interactive buttons.
    * `/requests`: Users can view the status of all their own pending requests.
* **Smart Caching:** Search and discover results are cached for 1 hour to reduce API spam and improve speed.

---

## 🚀 Getting Started

### Prerequisites

1.  A **Telegram Bot**. Get your `BOT_TOKEN` from [BotFather](https://t.me/botfather).
2.  Your **Telegram API ID & Hash**. Get these from [my.telegram.org](https://my.telegram.org).
3.  A **Jellyfin** server. You need your **Server URL** and an **API Key** (generate one in Dashboard > API Keys).
4.  A **Jellyseerr** server. You need your **Server URL** and your **API Key** (find in Jellyseerr Settings > General).
5.  **Python 3.12+**
6.  **Pipenv** (for managing dependencies).

### ⚙️ Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/DESTROYER-32/TellySeerr.git](https://github.com/DESTROYER-32/TellySeerr.git)
    cd your-repo-name
    ```

2.  **Install dependencies using Pipenv:**
    ```bash
    pipenv install
    ```
    This will create a virtual environment and install all packages from the `Pipfile.lock`.

3.  **Configure your bot:**
    Copy the sample environment file to create your own secret file.
    ```bash
    cp .env.sample .env
    ```
    Now, edit the `.env` file with your API keys and URLs. It's crucial that you **do not** use quotes (`"`) around the values.

    ```ini
    # --- .env file ---
    TELEGRAM_API_ID=1234567
    TELEGRAM_API_HASH=your_api_hash_here
    TELEGRAM_BOT_TOKEN=your_bot_token_here

    JELLYSEERR_URL=[https://jellyseerr.example.com](https://jellyseerr.example.com)
    JELLYSEERR_API_KEY=your_jellyseerr_api_key_here

    JELLYFIN_URL=[https://jellyfin.example.com](https://jellyfin.example.com)
    JELLYFIN_API_KEY=your_jellyfin_api_key_here

    # Your personal Telegram User ID
    ADMIN_USER_IDS=[123456789, 987654321]
    ```

4.  **Run the bot:**
    ```bash
    pipenv run python main.py
    ```
    The bot will start, connect to Telegram, set its commands, and initialize the database.

---

## 🤖 Bot Commands

The bot will automatically set these commands in the Telegram menu for you. Admins will see an extended list.

### User Commands
| Command | Description |
| --- | --- |
| `/start` | Start the bot |
| `/help` | Show the help message |
| `/request` | Request a movie/show. Usage: `/request <name>` |
| `/discover` | Discover popular and trending media |
| `/requests` | View your pending media requests |
| `/watch` | See your personal watch statistics |
| `/link` | Link your Jellyfin account. Usage: `/link <user> <pass>` |
| `/unlink` | Unlink your Jellyfin account |

### Admin-Only Commands
| Command | Description |
| --- | --- |
| `/invite` | Reply to a user to create a permanent account |
| `/trial` | Reply to a user to create a 7-day trial |
| `/vip` | Reply to a user to create a 30-day VIP account |
| `/deleteuser` | Delete a user. Usage: `/deleteuser <username>` |
| `/listusers` | List all users on the Jellyfin server |

---

## 🤝 Contributing

Contributions are welcome! If you'd like to fix a bug or add a new feature, please read the `CONTRIBUTING.md` file for details on how to:

* Report bugs and suggest features
* Set up your development environment
* Follow the code style and submit your changes

---

## 📜 License

This project is licensed under the MIT License. See the `LICENSE` file for details.