import os
import json
import time
import random
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
from rich.console import Console
from rich.progress import Progress
from rich.prompt import Prompt, Confirm
from rich.table import Table
from cryptography.fernet import Fernet
from instagrapi import Client
from instagrapi.exceptions import LoginRequired
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('instagram_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class InstagramAccountManager:
    def __init__(self):
        self.console = Console()
        self.accounts: Dict[str, Client] = {}
        self.encryption_key = self._get_or_create_key()
        self.fernet = Fernet(self.encryption_key)
        self.sessions_file = Path("sessions.enc")
        self.whitelist_file = Path("whitelist.json")
        self.load_sessions()
        self.whitelist = self._load_whitelist()
        self.UNFOLLOW_DELAY = random.uniform(1, 3)
        self.DAILY_UNFOLLOW_LIMIT = 200
        
    def _get_or_create_key(self) -> bytes:
        """Get existing encryption key or create a new one."""
        key_file = Path(".key")
        if key_file.exists():
            return key_file.read_bytes()
        key = Fernet.generate_key()
        key_file.write_bytes(key)
        return key

    def _load_whitelist(self) -> List[str]:
        """Load whitelist from file."""
        if self.whitelist_file.exists():
            with open(self.whitelist_file) as f:
                return json.load(f)
        return []

    def save_sessions(self):
        """Save account sessions securely."""
        sessions = {}
        for username, client in self.accounts.items():
            sessions[username] = {
                'settings': client.get_settings(),
                'session': client.get_settings()
            }
        encrypted_data = self.fernet.encrypt(json.dumps(sessions).encode())
        self.sessions_file.write_bytes(encrypted_data)
        logger.info("Sessions saved successfully")

    def load_sessions(self):
        """Load saved sessions."""
        if not self.sessions_file.exists():
            return
        
        try:
            encrypted_data = self.sessions_file.read_bytes()
            sessions = json.loads(self.fernet.decrypt(encrypted_data))
            
            for username, data in sessions.items():
                client = Client()
                client.set_settings(data['settings'])
                client.set_settings(data['session'])
                try:
                    client.get_timeline_feed()  # Verify session
                    self.accounts[username] = client
                    logger.info(f"Loaded session for {username}")
                except LoginRequired:
                    logger.warning(f"Session expired for {username}")
        except Exception as e:
            logger.error(f"Error loading sessions: {e}")

    def add_account(self, username: str, password: str):
        """Add a new Instagram account."""
        try:
            client = Client()
            client.login(username, password)
            self.accounts[username] = client
            self.save_sessions()
            logger.info(f"Successfully added account: {username}")
            return True
        except Exception as e:
            logger.error(f"Failed to add account {username}: {e}")
            return False

    def remove_account(self, username: str):
        """Remove an Instagram account."""
        if username in self.accounts:
            del self.accounts[username]
            self.save_sessions()
            logger.info(f"Removed account: {username}")
            return True
        return False

    def get_relationship_stats(self, username: str) -> Dict:
        """Get follower/following statistics for an account."""
        if username not in self.accounts:
            raise ValueError("Account not found")

        client = self.accounts[username]
        user_id = client.user_id

        with Progress() as progress:
            followers_task = progress.add_task("Fetching followers...", total=100)
            following_task = progress.add_task("Fetching following...", total=100)

            followers = client.user_followers(user_id)
            progress.update(followers_task, completed=100)

            following = client.user_following(user_id)
            progress.update(following_task, completed=100)

        followers_set = set(followers.keys())
        following_set = set(following.keys())
        
        non_mutual = following_set - followers_set
        
        stats = {
            'total_followers': len(followers),
            'total_following': len(following),
            'ratio': len(followers) / len(following) if len(following) > 0 else 0,
            'non_mutual_count': len(non_mutual),
            'non_mutual': non_mutual
        }
        
        return stats

    def smart_unfollow(self, username: str, exclude_verified: bool = True, 
                      exclude_business: bool = True):
        """Implement smart unfollowing with safety features."""
        if username not in self.accounts:
            raise ValueError("Account not found")

        client = self.accounts[username]
        stats = self.get_relationship_stats(username)
        non_mutual = stats['non_mutual']

        # Backup following list
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"following_backup_{timestamp}.csv"
        following_data = []
        for user_id in client.user_following(client.user_id).keys():
            user_info = client.user_info(user_id)
            following_data.append({
                'user_id': user_id,
                'username': user_info.username,
                'full_name': user_info.full_name
            })
        pd.DataFrame(following_data).to_csv(backup_file, index=False)

        unfollowed_count = 0
        with Progress() as progress:
            task = progress.add_task("Unfollowing non-mutual followers...", 
                                   total=len(non_mutual))

            for user_id in non_mutual:
                if unfollowed_count >= self.DAILY_UNFOLLOW_LIMIT:
                    logger.warning("Daily unfollow limit reached")
                    break

                try:
                    user_info = client.user_info(user_id)
                    
                    # Check exclusion criteria
                    if (user_info.username in self.whitelist or
                        (exclude_verified and user_info.is_verified) or
                        (exclude_business and user_info.is_business)):
                        continue

                    if Confirm.ask(f"Unfollow @{user_info.username}?"):
                        client.user_unfollow(user_id)
                        unfollowed_count += 1
                        time.sleep(self.UNFOLLOW_DELAY)
                        logger.info(f"Unfollowed @{user_info.username}")
                
                except Exception as e:
                    logger.error(f"Error unfollowing user {user_id}: {e}")
                
                progress.update(task, advance=1)

        return unfollowed_count

    def display_menu(self):
        """Display main menu interface."""
        while True:
            self.console.clear()
            self.console.print("[bold blue]Instagram Account Manager[/bold blue]")
            
            menu = Table(show_header=True, header_style="bold magenta")
            menu.add_column("Option", style="dim")
            menu.add_column("Description")
            
            menu.add_row("1", "Add Account")
            menu.add_row("2", "Remove Account")
            menu.add_row("3", "View Account Statistics")
            menu.add_row("4", "Smart Unfollow")
            menu.add_row("5", "Manage Whitelist")
            menu.add_row("6", "Exit")
            
            self.console.print(menu)
            
            choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4", "5", "6"])
            
            try:
                if choice == "1":
                    username = Prompt.ask("Enter Instagram username")
                    password = Prompt.ask("Enter password", password=True)
                    self.add_account(username, password)
                
                elif choice == "2":
                    if not self.accounts:
                        self.console.print("No accounts to remove!", style="red")
                        continue
                    
                    username = Prompt.ask("Enter username to remove", 
                                        choices=list(self.accounts.keys()))
                    self.remove_account(username)
                
                elif choice == "3":
                    if not self.accounts:
                        self.console.print("No accounts available!", style="red")
                        continue
                    
                    username = Prompt.ask("Select account", 
                                        choices=list(self.accounts.keys()))
                    stats = self.get_relationship_stats(username)
                    
                    stats_table = Table(title=f"Statistics for @{username}")
                    stats_table.add_column("Metric", style="cyan")
                    stats_table.add_column("Value", style="magenta")
                    
                    stats_table.add_row("Followers", str(stats['total_followers']))
                    stats_table.add_row("Following", str(stats['total_following']))
                    stats_table.add_row("Ratio", f"{stats['ratio']:.2f}")
                    stats_table.add_row("Non-mutual", str(stats['non_mutual_count']))
                    
                    self.console.print(stats_table)
                    Prompt.ask("Press Enter to continue")
                
                elif choice == "4":
                    if not self.accounts:
                        self.console.print("No accounts available!", style="red")
                        continue
                    
                    username = Prompt.ask("Select account", 
                                        choices=list(self.accounts.keys()))
                    exclude_verified = Confirm.ask("Exclude verified accounts?")
                    exclude_business = Confirm.ask("Exclude business accounts?")
                    
                    if Confirm.ask("Start unfollowing?"):
                        count = self.smart_unfollow(username, exclude_verified, 
                                                  exclude_business)
                        self.console.print(f"Unfollowed {count} users")
                        Prompt.ask("Press Enter to continue")
                
                elif choice == "5":
                    while True:
                        self.console.clear()
                        self.console.print("[bold blue]Whitelist Management[/bold blue]")
                        
                        whitelist_table = Table(show_header=True)
                        whitelist_table.add_column("Username")
                        for username in self.whitelist:
                            whitelist_table.add_row(username)
                        
                        self.console.print(whitelist_table)
                        
                        wl_choice = Prompt.ask(
                            "Select action",
                            choices=["add", "remove", "back"]
                        )
                        
                        if wl_choice == "add":
                            username = Prompt.ask("Enter username to whitelist")
                            if username not in self.whitelist:
                                self.whitelist.append(username)
                                with open(self.whitelist_file, 'w') as f:
                                    json.dump(self.whitelist, f)
                        
                        elif wl_choice == "remove":
                            if self.whitelist:
                                username = Prompt.ask(
                                    "Select username to remove",
                                    choices=self.whitelist
                                )
                                self.whitelist.remove(username)
                                with open(self.whitelist_file, 'w') as f:
                                    json.dump(self.whitelist, f)
                            else:
                                self.console.print("Whitelist is empty!", style="red")
                                Prompt.ask("Press Enter to continue")
                        
                        elif wl_choice == "back":
                            break
                
                elif choice == "6":
                    break
            
            except Exception as e:
                logger.error(f"Error in menu operation: {e}")
                self.console.print(f"Error: {str(e)}", style="red")
                Prompt.ask("Press Enter to continue")

if __name__ == "__main__":
    manager = InstagramAccountManager()
    manager.display_menu()
