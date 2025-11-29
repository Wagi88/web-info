#!/usr/bin/env python3
"""
finding-nemo - Social Media Account Finder
A Sherlock-inspired tool to find social media accounts by username
"""

import requests
import json
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class FindingNemo:
    def __init__(self):
        self.platforms = self.load_platforms()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        })
        
    def load_platforms(self):
        platforms = {
            "Facebook": {
                "url": "https://www.facebook.com/{}",
                "error": ["content-login-button", "login_form"]
            },
            "Instagram": {
                "url": "https://www.instagram.com/{}/",
                "error": ["The link you followed may be broken"]
            },
            "Twitter": {
                "url": "https://twitter.com/{}",
                "error": ["This account doesn't exist"]
            },
            "GitHub": {
                "url": "https://github.com/{}",
                "error": ["This is not the web page you are looking for"]
            },
            "YouTube": {
                "url": "https://www.youtube.com/@{}",
                "error": ["This channel doesn't exist"]
            },
            "Reddit": {
                "url": "https://www.reddit.com/user/{}",
                "error": ["Sorry, nobody on Reddit goes by that name"]
            },
            "Pinterest": {
                "url": "https://www.pinterest.com/{}/",
                "error": ["Sorry, we couldn't find"]
            },
            "TikTok": {
                "url": "https://www.tiktok.com/@{}",
                "error": ["Couldn't find this account"]
            },
            "LinkedIn": {
                "url": "https://www.linkedin.com/in/{}",
                "error": ["This page doesn't exist"]
            },
            "Twitch": {
                "url": "https://www.twitch.tv/{}",
                "error": ["the page you are looking for is unavailable"]
            },
            "Telegram": {
                "url": "https://t.me/{}",
                "error": ["If you have Telegram, you can contact"]
            },
            "VK": {
                "url": "https://vk.com/{}",
                "error": ["Error 404"]
            },
            "Medium": {
                "url": "https://medium.com/@{}",
                "error": ["404"]
            },
            "DevianArt": {
                "url": "https://{}.deviantart.com",
                "error": ["404"]
            },
            "Spotify": {
                "url": "https://open.spotify.com/user/{}",
                "error": ["Page not found"]
            }
        }
        return platforms

    def check_platform(self, platform, username):
        platform_data = self.platforms[platform]
        url = platform_data["url"].format(username)
        
        try:
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                # Check for error indicators in response text
                error_indicators = platform_data.get("error", [])
                found = True
                
                for error in error_indicators:
                    if error.lower() in response.text.lower():
                        found = False
                        break
                
                return platform, url, found, "Success"
            else:
                return platform, url, False, f"Status: {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            return platform, url, False, f"Error: {str(e)}"

    def print_banner(self):
        banner = f"""
{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║    ███████╗██╗██╗  ██╗██████╗ ██╗███╗   ██╗ ██████╗         ║
║    ██╔════╝██║██║  ██║██╔══██╗██║████╗  ██║██╔════╝         ║
║    █████╗  ██║███████║██║  ██║██║██╔██╗ ██║██║              ║
║    ██╔══╝  ██║██╔══██║██║  ██║██║██║╚██╗██║██║              ║
║    ██║     ██║██║  ██║██████╔╝██║██║ ╚████║╚██████╗         ║
║    ╚═╝     ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝         ║
║                                                              ║
║              FINDING-NEMO - Social Media Finder             ║
║                     Created for Termux                      ║
╚══════════════════════════════════════════════════════════════╝
{Colors.RESET}
        """
        print(banner)

    def print_result(self, platform, url, found, message):
        if found:
            status = f"{Colors.GREEN}[ FOUND ]{Colors.RESET}"
            print(f"{status} {Colors.BOLD}{platform}{Colors.RESET}")
            print(f"     {Colors.CYAN}URL: {Colors.WHITE}{url}{Colors.RESET}")
        else:
            status = f"{Colors.RED}[ NOT FOUND ]{Colors.RESET}"
            print(f"{status} {Colors.BOLD}{platform}{Colors.RESET}")

    def run_search(self, username):
        print(f"\n{Colors.YELLOW}[*] Searching for username: {Colors.BOLD}{username}{Colors.RESET}")
        print(f"{Colors.YELLOW}[*] Scanning {len(self.platforms)} platforms...{Colors.RESET}\n")
        
        found_count = 0
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_platform = {
                executor.submit(self.check_platform, platform, username): platform 
                for platform in self.platforms
            }
            
            for future in as_completed(future_to_platform):
                platform, url, found, message = future.result()
                self.print_result(platform, url, found, message)
                if found:
                    found_count += 1
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print(f"\n{Colors.GREEN}[+] Scan completed in {elapsed_time:.2f} seconds")
        print(f"{Colors.GREEN}[+] Found {found_count} accounts for '{username}'{Colors.RESET}")

    def interactive_mode(self):
        self.print_banner()
        
        while True:
            try:
                print(f"\n{Colors.CYAN}┌──[{Colors.WHITE}finding-nemo{Colors.CYAN}]─[{Colors.WHITE}~{Colors.CYAN}]")
                username = input(f"{Colors.CYAN}└─{Colors.YELLOW}$ {Colors.RESET}").strip()
                
                if not username:
                    continue
                    
                if username.lower() in ['exit', 'quit', 'q']:
                    print(f"\n{Colors.YELLOW}[!] Goodbye!{Colors.RESET}")
                    break
                    
                self.run_search(username)
                
            except KeyboardInterrupt:
                print(f"\n\n{Colors.YELLOW}[!] Operation cancelled by user{Colors.RESET}")
                break
            except Exception as e:
                print(f"\n{Colors.RED}[!] Error: {str(e)}{Colors.RESET}")

def main():
    if len(sys.argv) > 1:
        username = sys.argv[1]
        finder = FindingNemo()
        finder.print_banner()
        finder.run_search(username)
    else:
        finder = FindingNemo()
        finder.interactive_mode()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}[!] Program terminated by user{Colors.RESET}")
    except Exception as e:
        print(f"\n{Colors.RED}[!] Unexpected error: {str(e)}{Colors.RESET}")
