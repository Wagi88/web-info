import socket
import requests
import json
import time
import threading
from datetime import datetime
import sys
import signal
import subprocess
import platform
from urllib.parse import urlparse

class ServerInfoGatherer:
    def __init__(self):
        self.running = False
        self.scan_count = 0
        self.scanned_servers = set()
        self.geo_cache = {}
        
    def print_banner(self):
        banner = """
╔══════════════════════════════════════════════════════════════════════╗
║                   SERVER INFORMATION GATHERER                       ║
║                 Comprehensive Data Collection Tool                  ║
╚══════════════════════════════════════════════════════════════════════╝
        """
        print(banner)
    
    def print_status(self):
        status = f"""
┌─────────────────── TOOL STATUS ───────────────────┐
│  Running: {'YES' if self.running else 'NO':<10}                    │
│  Servers Scanned: {self.scan_count:<8}                  │
│  Unique Servers: {len(self.scanned_servers):<8}                    │
│  Press Ctrl+C to stop                              │
└────────────────────────────────────────────────────┘
        """
        print(status)
    
    def resolve_hostname(self, hostname):
        """Resolve hostname to IP address with additional info"""
        try:
            # Get all address info
            addr_info = socket.getaddrinfo(hostname, None)
            ips = set()
            for family, type, proto, canonname, sockaddr in addr_info:
                ip = sockaddr[0]
                ips.add(ip)
            
            # Get primary IP
            primary_ip = socket.gethostbyname(hostname)
            
            return {
                'primary_ip': primary_ip,
                'all_ips': list(ips),
                'hostname': hostname,
                'canonical_name': canonname if canonname != hostname else None
            }
        except socket.gaierror as e:
            return {'error': f"DNS resolution failed: {str(e)}"}
        except Exception as e:
            return {'error': f"Resolution error: {str(e)}"}
    
    def get_geolocation(self, ip):
        """Get geolocation information for IP"""
        if ip in self.geo_cache:
            return self.geo_cache[ip]
            
        try:
            response = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.geo_cache[ip] = data
                return data
        except:
            pass
        return None
    
    def port_scan(self, ip, ports=[80, 443, 22, 21, 25, 53, 110, 143, 993, 995]):
        """Quick port scan for common services"""
        open_ports = []
        for port in ports:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(1)
                    result = sock.connect_ex((ip, port))
                    if result == 0:
                        open_ports.append(port)
            except:
                continue
        return open_ports
    
    def get_service_info(self, ip, port):
        """Get service banner information"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(2)
                sock.connect((ip, port))
                
                # Try to receive banner
                if port in [80, 443]:
                    sock.send(b"HEAD / HTTP/1.0\r\n\r\n")
                elif port == 22:
                    sock.send(b"SSH-2.0-Client\r\n")
                
                banner = sock.recv(1024).decode('utf-8', errors='ignore')
                return banner.strip()[:200]  # Limit banner length
        except:
            return None
    
    def get_http_headers(self, ip):
        """Get HTTP headers from web server"""
        try:
            # Try HTTP
            response = requests.get(f"http://{ip}", timeout=5, allow_redirects=False)
            return {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'server': response.headers.get('Server', 'Unknown'),
                'via_http': True
            }
        except:
            try:
                # Try HTTPS
                response = requests.get(f"https://{ip}", timeout=5, allow_redirects=False)
                return {
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'server': response.headers.get('Server', 'Unknown'),
                    'via_https': True
                }
            except:
                return None
    
    def ping_server(self, ip):
        """Ping server to check responsiveness"""
        try:
            param = "-n" if platform.system().lower() == "windows" else "-c"
            command = ["ping", param, "2", ip]
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False
    
    def get_reverse_dns(self, ip):
        """Get reverse DNS (PTR) record"""
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except:
            return None
    
    def format_geolocation(self, geo_data):
        """Format geolocation information"""
        if not geo_data or geo_data.get('status') != 'success':
            return "Geolocation data unavailable"
        
        return f"""
    ┌─ Geolocation Information ──────────────────────────┐
    │ Country: {geo_data.get('country', 'Unknown'):<40} │
    │ Region: {geo_data.get('regionName', 'Unknown'):<41} │
    │ City: {geo_data.get('city', 'Unknown'):<44} │
    │ ISP: {geo_data.get('isp', 'Unknown'):<44} │
    │ Organization: {geo_data.get('org', 'Unknown'):<34} │
    │ AS: {geo_data.get('as', 'Unknown'):<45} │
    └────────────────────────────────────────────────────┘"""
    
    def format_port_info(self, ip, open_ports):
        """Format port information"""
        if not open_ports:
            return "    No common ports open"
        
        port_info = []
        for port in open_ports:
            service_name = self.get_service_name(port)
            banner = self.get_service_info(ip, port)
            status = f"Port {port} ({service_name})"
            if banner:
                status += f" - {banner.split(chr(10))[0][:50]}"
            port_info.append(status)
        
        result = "    ┌─ Open Ports & Services ───────────────────────────┐\n"
        for info in port_info:
            result += f"    │ {info:<47} │\n"
        result += "    └────────────────────────────────────────────────────┘"
        return result
    
    def get_service_name(self, port):
        """Get common service name for port"""
        services = {
            20: "FTP Data", 21: "FTP", 22: "SSH", 23: "Telnet",
            25: "SMTP", 53: "DNS", 80: "HTTP", 110: "POP3",
            143: "IMAP", 443: "HTTPS", 993: "IMAPS", 995: "POP3S",
            3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL"
        }
        return services.get(port, "Unknown")
    
    def format_http_info(self, http_info):
        """Format HTTP server information"""
        if not http_info:
            return "    HTTP/HTTPS not accessible"
        
        protocol = "HTTPS" if http_info.get('via_https') else "HTTP"
        server_type = http_info.get('server', 'Unknown')
        status = http_info.get('status_code', 'Unknown')
        
        return f"""
    ┌─ Web Server Information ─────────────────────────┐
    │ Protocol: {protocol:<40} │
    │ Status: {status:<41} │
    │ Server: {server_type:<41} │
    └────────────────────────────────────────────────────┘"""
    
    def gather_comprehensive_info(self, hostname):
        """Gather comprehensive information about server"""
        print(f"\n🔍 Gathering information for: {hostname}")
        print("─" * 60)
        
        # Resolve hostname
        resolution = self.resolve_hostname(hostname)
        if 'error' in resolution:
            print(f"❌ Error: {resolution['error']}")
            return None
        
        primary_ip = resolution['primary_ip']
        print(f"📍 Primary IP: {primary_ip}")
        
        if len(resolution['all_ips']) > 1:
            print(f"📡 All IPs: {', '.join(resolution['all_ips'])}")
        
        # Basic connectivity
        is_alive = self.ping_server(primary_ip)
        status_icon = "🟢" if is_alive else "🔴"
        print(f"{status_icon} Server responsive: {'Yes' if is_alive else 'No'}")
        
        # Reverse DNS
        reverse_dns = self.get_reverse_dns(primary_ip)
        if reverse_dns:
            print(f"🔁 Reverse DNS: {reverse_dns}")
        
        # Geolocation
        geo_data = self.get_geolocation(primary_ip)
        if geo_data:
            print(self.format_geolocation(geo_data))
        
        # Port scanning
        print("\n🔎 Scanning common ports...")
        open_ports = self.port_scan(primary_ip)
        print(self.format_port_info(primary_ip, open_ports))
        
        # HTTP information
        print("\n🌐 Checking web services...")
        http_info = self.get_http_headers(primary_ip)
        print(self.format_http_info(http_info))
        
        return {
            'ip': primary_ip,
            'all_ips': resolution['all_ips'],
            'geolocation': geo_data,
            'open_ports': open_ports,
            'http_info': http_info,
            'responsive': is_alive,
            'reverse_dns': reverse_dns,
            'timestamp': datetime.now().isoformat()
        }
    
    def continuous_monitoring(self, hostname, interval=30):
        """Continuously monitor server and gather information"""
        print(f"🚀 Starting continuous monitoring for: {hostname}")
        print(f"⏰ Update interval: {interval} seconds")
        print("─" * 60)
        
        self.running = True
        previous_data = None
        
        try:
            while self.running:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n🕐 Scan at: {timestamp}")
                print("=" * 60)
                
                current_data = self.gather_comprehensive_info(hostname)
                
                if current_data and current_data['ip'] not in self.scanned_servers:
                    self.scanned_servers.add(current_data['ip'])
                
                self.scan_count += 1
                
                # Update status every 3 scans
                if self.scan_count % 3 == 0:
                    self.print_status()
                
                print(f"\n⏳ Next scan in {interval} seconds...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop the monitoring"""
        self.running = False
        print("\n" + "=" * 60)
        print("🛑 Server Information Gatherer Stopped")
        print("=" * 60)
        self.print_final_summary()
    
    def print_final_summary(self):
        """Print final summary when tool stops"""
        summary = f"""
╔══════════════════════════════════════════════════════════════╗
║                       FINAL SUMMARY                         ║
╠══════════════════════════════════════════════════════════════╣
║  Total Scans Performed: {self.scan_count:>20}            ║
║  Unique Servers Found: {len(self.scanned_servers):>20}            ║
║  Geolocation Queries: {len(self.geo_cache):>21}            ║
║                                                        ║
║  Monitored Servers:                                      ║
"""
        print(summary)
        
        for i, server in enumerate(self.scanned_servers, 1):
            geo = self.geo_cache.get(server, {})
            country = geo.get('country', 'Unknown')
            print(f"║    {i:2d}. {server:<15} - {country:<25} ║")
        
        print("║                                                        ║")
        print("╚══════════════════════════════════════════════════════════════╝")
    
    def signal_handler(self, signum, frame):
        """Handle interrupt signals"""
        self.stop()
        sys.exit(0)

def main():
    tool = ServerInfoGatherer()
    
    # Set up signal handling for graceful shutdown
    signal.signal(signal.SIGINT, tool.signal_handler)
    
    # Display banner
    tool.print_banner()
    
    # Get user input
    print("Enter the server hostname to monitor:")
    print("Examples: google.com, github.com, example.com")
    print("─" * 50)
    
    hostname = input("Hostname: ").strip()
    
    if not hostname:
        print("No hostname provided. Using 'google.com' as default.")
        hostname = "google.com"
    
    print("\nEnter monitoring interval in seconds (default: 30):")
    try:
        interval = float(input("Interval: ").strip() or "30")
        if interval < 5:
            print("Interval too short. Using minimum of 5 seconds.")
            interval = 5
    except ValueError:
        print("Invalid input. Using default interval of 30 seconds.")
        interval = 30
    
    # Clear screen and start
    print("\n" * 3)
    tool.print_banner()
    
    # Start continuous monitoring
    tool.continuous_monitoring(hostname, interval)

if __name__ == "__main__":
    main()
