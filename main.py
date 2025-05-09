#!/usr/bin/env python3
# Instagram Follower Manager
# A tool to unfollow Instagram users who don't follow you back

import os
import time
import random
import getpass
import json
from typing import List, Dict

try:
    from instagrapi import Client
    from instagrapi.exceptions import LoginRequired, ClientError
except ImportError:
    print("Error: instagrapi module not found.")
    print("Please install it using: pip install instagrapi")
    exit(1)

class InstagramFollowerManager:
    def __init__(self):
        self.client = Client()
        self.user_id = None
        self.username = None
        self.followers = []
        self.following = []
        self.non_followers = []
        self.session_file = "session.json"
        
    def save_session(self):
        """Save session data to file"""
        session = self.client.get_settings()
        with open(self.session_file, 'w') as f:
            json.dump(session, f)
            
    def load_session(self) -> bool:
        """Load session data from file"""
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r') as f:
                    session = json.load(f)
                    self.client.set_settings(session)
                    self.client.login(self.username, "")
                    return True
        except Exception:
            pass
        return False
        
    def login(self, username: str, password: str) -> bool:
        """Login to Instagram account"""
        try:
            print("Logging in to Instagram...")
            self.username = username
            
            # Try to load existing session first
            if self.load_session():
                print(f"Successfully logged in as {username} using saved session")
                self.user_id = self.client.user_id
                return True
                
            # If session loading fails, do fresh login
            self.client.login(username, password)
            self.user_id = self.client.user_id
            self.save_session()
            print(f"Successfully logged in as {username}")
            return True
            
        except Exception as e:
            print(f"Login failed: {e}")
            return False
            
    def get_followers(self) -> List[Dict]:
        """Get account followers"""
        print("Fetching followers...")
        try:
            followers = self.client.user_followers(self.user_id, amount=0)
            self.followers = [
                {
                    "pk": user_id,
                    "username": user_info.username,
                    "full_name": user_info.full_name
                }
                for user_id, user_info in followers.items()
            ]
            print(f"Found {len(self.followers)} followers")
            return self.followers
        except LoginRequired:
            print("Session expired. Please login again.")
            return []
        except Exception as e:
            print(f"Error getting followers: {e}")
            return []
    
    def get_following(self) -> List[Dict]:
        """Get accounts the user is following"""
        print("Fetching following...")
        try:
            following = self.client.user_following(self.user_id, amount=0)
            self.following = [
                {
                    "pk": user_id,
                    "username": user_info.username,
                    "full_name": user_info.full_name
                }
                for user_id, user_info in following.items()
            ]
            print(f"Found {len(self.following)} accounts you're following")
            return self.following
        except LoginRequired:
            print("Session expired. Please login again.")
            return []
        except Exception as e:
            print(f"Error getting following: {e}")
            return []
    
    def find_non_followers(self) -> List[Dict]:
        """Find accounts that don't follow back"""
        follower_ids = [user["pk"] for user in self.followers]
        self.non_followers = [
            user for user in self.following 
            if user["pk"] not in follower_ids
        ]
        print(f"Found {len(self.non_followers)} accounts that don't follow you back")
        return self.non_followers
    
    def unfollow_users(self, user_ids: List[str], delay_range: tuple = (30, 60)) -> None:
        """Unfollow selected users with random delays"""
        total = len(user_ids)
        retries = 3
        
        for index, user_id in enumerate(user_ids, 1):
            retry_count = 0
            while retry_count < retries:
                try:
                    user_info = next((user for user in self.non_followers if user["pk"] == user_id), None)
                    if not user_info:
                        break
                        
                    print(f"[{index}/{total}] Unfollowing @{user_info['username']}...")
                    result = self.client.user_unfollow(user_id)
                    
                    if result:
                        print(f"Successfully unfollowed @{user_info['username']}")
                        # Save session after successful unfollow
                        self.save_session()
                        break
                    else:
                        print(f"Failed to unfollow @{user_info['username']}")
                        retry_count += 1
                    
                except LoginRequired:
                    print("Session expired. Attempting to refresh login...")
                    if not self.load_session():
                        print("Could not refresh session. Please restart the program.")
                        return
                    retry_count += 1
                    
                except ClientError as e:
                    print(f"Instagram API error: {e}")
                    retry_count += 1
                    time.sleep(120)  # Longer delay on API errors
                    
                except Exception as e:
                    print(f"Error unfollowing user: {e}")
                    retry_count += 1
                    time.sleep(60)  # Standard delay on other errors
                    
                if retry_count >= retries:
                    print(f"Failed to unfollow @{user_info['username']} after {retries} attempts")
                    
            # Random delay between unfollows
            if index < total:
                delay = random.uniform(delay_range[0], delay_range[1])
                print(f"Waiting {delay:.1f} seconds before next unfollow...")
                time.sleep(delay)
    
    def interactive_unfollow(self) -> None:
        """Interactive menu to select and unfollow users"""
        if not self.non_followers:
            print("No non-followers found.")
            return
            
        while True:
            print("\n" + "=" * 50)
            print("ACCOUNTS THAT DON'T FOLLOW YOU BACK")
            print("=" * 50)
            
            for i, user in enumerate(self.non_followers, 1):
                print(f"{i}. @{user['username']} - {user['full_name']}")
            
            print("\n[A] Unfollow all")
            print("[S] Select specific users to unfollow")
            print("[Q] Quit without unfollowing")
            
            choice = input("\nEnter your choice: ").strip().upper()
            
            if choice == 'A':
                confirm = input("Are you sure you want to unfollow ALL non-followers? (y/n): ").strip().lower()
                if confirm == 'y':
                    user_ids = [user["pk"] for user in self.non_followers]
                    self.unfollow_users(user_ids)
                break
                
            elif choice == 'S':
                selected_indices = input("Enter the numbers of users to unfollow (comma-separated): ").strip()
                try:
                    indices = [int(x.strip()) - 1 for x in selected_indices.split(',')]
                    selected_users = [self.non_followers[i] for i in indices if 0 <= i < len(self.non_followers)]
                    
                    if selected_users:
                        user_ids = [user["pk"] for user in selected_users]
                        self.unfollow_users(user_ids)
                    else:
                        print("No valid users selected.")
                except (ValueError, IndexError):
                    print("Invalid input. Please enter comma-separated numbers.")
                break
                
            elif choice == 'Q':
                print("Exiting without unfollowing any users.")
                break
                
            else:
                print("Invalid choice. Please try again.")

def main():
    print("=" * 60)
    print("INSTAGRAM FOLLOWER MANAGER")
    print("=" * 60)
    print("This tool helps you identify and unfollow Instagram users who don't follow you back.")
    print("Your login information is only used locally and is not stored or shared.")
    print("=" * 60)
    
    username = input("Enter your Instagram username: ")
    password = getpass.getpass("Enter your Instagram password: ")
    
    manager = InstagramFollowerManager()
    
    if manager.login(username, password):
        manager.get_followers()
        manager.get_following()
        manager.find_non_followers()
        manager.interactive_unfollow()
    
    print("\nThank you for using Instagram Follower Manager!")

if __name__ == "__main__":
    main()