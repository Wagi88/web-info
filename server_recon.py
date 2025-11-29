#!/usr/bin/env python3
"""
Server Reconnaissance Tool for Termux
A beautiful and clean tool to gather server information and data from hidden pages.
"""

import requests
import socket
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import colorama
from colorama import Fore, Style
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor

# Initialize colorama for cross-platform colored output
colorama.init(autoreset=True)

# Common hidden paths to check
HIDDEN_PATHS = [
    "admin", "dashboard", "login", "wp-admin", "phpmyadmin",
    ".git", ".env", "backup", "api", "config", "uploads",
    "administrator", "mysql", "test", "hidden", "cgi-bin",
    "phpinfo.php", "robots.txt", ".htaccess", "backup.zip",
    "wp-login.php", "administrator/index.php", "server-status"
]

# Common ports to scan
COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 443, 993, 995, 1723, 3306, 3389, 5900, 8080, 8443]

def print_banner():
    """Print the tool banner."""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║               SERVER RECONNAISSANCE TOOL                    ║")
    print("║                    For Termux Environment                   ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(Style.RESET_ALL)

def print_header(title):
    """Print a beautiful section header."""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Style.BRIGHT}{title}")
    print(f"{'='*60}{Style.RESET_ALL}")

def print_success(message):
    """Print a success message."""
    print(f"{Fore.GREEN}[+] {message}")

def print_warning(message):
    """Print a warning message."""
    print(f"{Fore.YELLOW}[!] {message}")

def print_error(message):
    """Print an error message."""
    print(f"{Fore.RED}[-] {message}")

def print_info(message):
    """Print an info message."""
    print(f"{Fore.BLUE}[*] {message}")

def validate_url(url):
    """Validate and format the target URL."""
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
        print_warning(f"Added http:// prefix. Using: {url}")
    return url

def get_target():
    """Get and validate target server from user input."""
    print_banner()
    print(f"{Fore.YELLOW}NOTE: Only use this tool on servers you own or have permission to test!")
    print(f"{Fore.RED}Unauthorized scanning is illegal and unethical!{Style.RESET_ALL}\n")
    
    while True:
        target = input(f"{Fore.WHITE}Enter target server (domain or IP): ").strip()
        if target:
            try:
                validated_target = validate_url(target)
                # Test if the target is reachable
                print_info("Testing connection to target...")
                response = requests.get(validated_target, timeout=10)
                print_success(f"Target is reachable! Status: {response.status_code}")
                return validated_target
            except requests.exceptions.RequestException as e:
                print_warning(f"Initial connection failed: {str(e)}")
                choice = input("Continue anyway? (y/n): ").lower()
                if choice == 'y':
                    return validated_target
                else:
                    continue
        else:
            print_error("Please enter a valid target.")

def get_server_info(url):
    """Gather basic server and DNS information."""
    print_header("SERVER & DNS INFORMATION")
    
    try:
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname
        
        # Get IP Address
        ip_address = socket.gethostbyname(hostname)
        print_success(f"IP Address: {ip_address}")
        
        # Get Server Header from HTTP response
        try:
            response = requests.get(url, timeout=10)
            print_success(f"HTTP Status: {response.status_code}")
            
            # Server headers
            server_header = response.headers.get('Server', 'Not Found')
            print_success(f"Server Software: {server_header}")
            
            # Other interesting headers
            interesting_headers = ['X-Powered-By', 'X-Frame-Options', 'Content-Type', 
                                 'Content-Length', 'Cache-Control', 'X-Content-Type-Options']
            for header in interesting_headers:
                if header in response.headers:
                    print_info(f"{header}: {response.headers[header]}")
                    
        except Exception as e:
            print_error(f"HTTP request failed: {str(e)}")
            
    except Exception as e:
        print_error(f"Server info gathering failed: {str(e)}")

def scan_port(hostname, port):
    """Scan a single port."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((hostname, port))
        sock.close()
        return port, result == 0
    except:
        return port, False

def port_scan(hostname):
    """Perform a threaded port scan."""
    print_header("PORT SCAN RESULTS")
    print_info(f"Scanning {len(COMMON_PORTS)} common ports on {hostname}...")
    
    open_ports = []
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(scan_port, hostname, port) for port in COMMON_PORTS]
        
        for future in futures:
            port, is_open = future.result()
            if is_open:
                open_ports.append(port)
                # Get service name
                try:
                    service = socket.getservbyport(port, 'tcp')
                except:
                    service = "unknown"
                print_success(f"Port {port}/tcp is OPEN - {service}")
    
    if open_ports:
        print_success(f"Found {len(open_ports)} open ports")
    else:
        print_info("No common open ports found.")

def scrape_web_content(url):
    """Scrape visible web content using BeautifulSoup."""
    print_header("WEB CONTENT ANALYSIS")
    
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Get Page Title
        title = soup.title.string if soup.title else "No Title Found"
        print_success(f"Page Title: {title}")
        
        # Get Meta Description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            desc = meta_desc['content'][:100] + "..." if len(meta_desc['content']) > 100 else meta_desc['content']
            print_info(f"Meta Description: {desc}")
        
        # Get All Links
        links = soup.find_all('a', href=True)
        print_info(f"Found {len(links)} links on the page.")
        
        # Categorize and display links
        internal_links = []
        external_links = []
        
        for link in links:
            full_url = urljoin(url, link['href'])
            if urlparse(full_url).netloc == urlparse(url).netloc:
                internal_links.append(full_url)
            else:
                external_links.append(full_url)
        
        if internal_links:
            print_success(f"Internal links ({len(internal_links)}):")
            for link in internal_links[:5]:
                print(f"  → {link}")
            if len(internal_links) > 5:
                print_info(f"  ... and {len(internal_links) - 5} more internal links")
                
        if external_links:
            print_warning(f"External links ({len(external_links)}):")
            for link in external_links[:3]:
                print(f"  → {link}")
            
    except Exception as e:
        print_error(f"Web scraping failed: {str(e)}")

def check_hidden_path(url, path):
    """Check a single hidden path."""
    test_url = urljoin(url, path)
    try:
        response = requests.get(test_url, timeout=5)
        if response.status_code in [200, 301, 302, 403]:
            return test_url, response.status_code, len(response.content)
    except:
        pass
    return None

def find_hidden_paths(url):
    """Brute-force common hidden directories and files using threading."""
    print_header("HIDDEN PATH DISCOVERY")
    print_info(f"Checking {len(HIDDEN_PATHS)} common hidden paths...")
    
    found_paths = []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(check_hidden_path, url, path) for path in HIDDEN_PATHS]
        
        for future in futures:
            result = future.result()
            if result:
                test_url, status_code, content_length = result
                found_paths.append(test_url)
                
                status_color = Fore.GREEN if status_code == 200 else Fore.YELLOW
                print_success(f"Found: {test_url} (Status: {status_color}{status_code}{Style.RESET_ALL}, Size: {content_length} bytes)")
    
    if not found_paths:
        print_info("No common hidden paths found.")
    else:
        print_success(f"Found {len(found_paths)} accessible hidden paths!")

def advanced_content_discovery(url):
    """Advanced discovery for hidden form fields and comments."""
    print_header("ADVANCED CONTENT DISCOVERY")
    
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find hidden input fields
        hidden_inputs = soup.find_all('input', type='hidden')
        if hidden_inputs:
            print_info(f"Found {len(hidden_inputs)} hidden form fields:")
            for inp in hidden_inputs:
                name = inp.get('name', 'unnamed')
                value = inp.get('value', 'no value')
                value_preview = value[:50] + "..." if len(value) > 50 else value
                print(f"  - {name} = {value_preview}")
        else:
            print_info("No hidden form fields found.")
        
        # Find HTML comments
        comments = soup.find_all(string=lambda text: isinstance(text, str) and '<!--' in text and '-->' in text)
        if comments:
            print_info(f"Found {len(comments)} HTML comments:")
            for i, comment in enumerate(comments[:5]):  # Show first 5
                clean_comment = ' '.join(comment.strip().split())
                preview = clean_comment[:100] + "..." if len(clean_comment) > 100 else clean_comment
                print(f"  Comment {i+1}: {preview}")
        else:
            print_info("No HTML comments found.")
            
        # Find JavaScript files
        scripts = soup.find_all('script', src=True)
        if scripts:
            print_info(f"Found {len(scripts)} external JavaScript files:")
            for script in scripts[:3]:
                print(f"  → {urljoin(url, script['src'])}")
                
    except Exception as e:
        print_error(f"Advanced discovery failed: {str(e)}")

def check_robots_txt(url):
    """Check robots.txt for interesting paths."""
    print_header("ROBOTS.TXT ANALYSIS")
    
    robots_url = urljoin(url, '/robots.txt')
    try:
        response = requests.get(robots_url, timeout=5)
        if response.status_code == 200:
            print_success("robots.txt found!")
            lines = response.text.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and ('Disallow:' in line or 'Allow:' in line):
                    print(f"  {line}")
        else:
            print_info("No robots.txt found or not accessible")
    except:
        print_info("Failed to fetch robots.txt")

def main():
    """Main function to run all reconnaissance tasks."""
    try:
        target = get_target()
        parsed_url = urlparse(target)
        hostname = parsed_url.hostname
        
        print_info(f"Starting comprehensive reconnaissance on: {target}")
        start_time = time.time()
        
        # Execute all reconnaissance functions
        get_server_info(target)
        port_scan(hostname)
        scrape_web_content(target)
        check_robots_txt(target)
        find_hidden_paths(target)
        advanced_content_discovery(target)
        
        end_time = time.time()
        print_header("RECONNAISSANCE COMPLETE")
        print_success(f"All tasks finished in {end_time - start_time:.2f} seconds!")
        print(f"\n{Fore.YELLOW}Summary Report:")
        print(f"  Target: {target}")
        print(f"  Hostname: {hostname}")
        print(f"  Scan duration: {end_time - start_time:.2f} seconds")
        print(f"\n{Fore.RED}Remember: Use this tool ethically and legally!")
        print(f"{Fore.RED}Only scan systems you own or have explicit permission to test!")
        
    except KeyboardInterrupt:
        print_error("\nScan interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
