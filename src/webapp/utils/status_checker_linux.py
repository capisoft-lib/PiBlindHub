"""
Linux-specific network status checker
"""

import asyncio
import subprocess
import socket
import re
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class LinuxStatusChecker:
    """Network status checker for Linux systems"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def get_wifi_status(self) -> Dict[str, Any]:
        """Get WiFi connection status"""
        try:
            # Check if we have wireless interfaces
            wireless_interfaces = await self._get_wireless_interfaces()
            
            if not wireless_interfaces:
                return {
                    "status": "not_available",
                    "connected": False,
                    "ssid": None,
                    "signal_strength": None,
                    "interface": None,
                    "ip_address": None
                }
            
            # Check connection status for each wireless interface
            for interface in wireless_interfaces:
                connection_info = await self._check_wireless_connection(interface)
                if connection_info["connected"]:
                    return {
                        "status": "connected",
                        "connected": True,
                        "ssid": connection_info.get("ssid"),
                        "signal_strength": connection_info.get("signal_strength"),
                        "interface": interface,
                        "ip_address": await self._get_interface_ip(interface)
                    }
            
            return {
                "status": "disconnected",
                "connected": False,
                "ssid": None,
                "signal_strength": None,
                "interface": wireless_interfaces[0] if wireless_interfaces else None,
                "ip_address": None
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get WiFi status: {e}")
            return {
                "status": "error",
                "connected": False,
                "ssid": None,
                "signal_strength": None,
                "interface": None,
                "ip_address": None,
                "error": str(e)
            }
    
    async def get_lan_status(self) -> Dict[str, Any]:
        """Get LAN connection status"""
        try:
            # Get ethernet interfaces
            ethernet_interfaces = await self._get_ethernet_interfaces()
            
            if not ethernet_interfaces:
                return {
                    "status": "not_connected",
                    "connected": False,
                    "interface": None,
                    "ip_address": None
                }
            
            # Check connection status for each ethernet interface
            for interface in ethernet_interfaces:
                if await self._is_interface_up(interface):
                    ip_address = await self._get_interface_ip(interface)
                    if ip_address and not ip_address.startswith("127."):
                        return {
                            "status": "connected",
                            "connected": True,
                            "interface": interface,
                            "ip_address": ip_address
                        }
            
            return {
                "status": "not_connected",
                "connected": False,
                "interface": ethernet_interfaces[0] if ethernet_interfaces else None,
                "ip_address": None
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get LAN status: {e}")
            return {
                "status": "error",
                "connected": False,
                "interface": None,
                "ip_address": None,
                "error": str(e)
            }
    
    async def get_hotspot_status(self) -> Dict[str, Any]:
        """Get hotspot status"""
        try:
            # Check if hostapd is running
            hostapd_running = await self._is_process_running("hostapd")
            
            if not hostapd_running:
                return {
                    "status": "Disabled",
                    "active": False,
                    "ssid": None,
                    "ip_address": None,
                    "clients": 0
                }
            
            # Get hotspot configuration
            hotspot_config = await self._get_hostapd_config()
            
            # Get hotspot IP address (usually on ap0 or wlan0)
            hotspot_interfaces = ["ap0", "wlan0"]
            hotspot_ip = None
            
            for interface in hotspot_interfaces:
                ip = await self._get_interface_ip(interface)
                if ip and ip.startswith("192.168."):  # Common hotspot IP range
                    hotspot_ip = ip
                    break
            
            # Get connected clients count
            clients_count = await self._get_hotspot_clients_count()
            
            return {
                "status": f"Active + {hotspot_ip}" if hotspot_ip else "Active",
                "active": True,
                "ssid": hotspot_config.get("ssid"),
                "ip_address": hotspot_ip,
                "clients": clients_count
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get hotspot status: {e}")
            return {
                "status": "Error",
                "active": False,
                "ssid": None,
                "ip_address": None,
                "clients": 0,
                "error": str(e)
            }
    
    async def _get_wireless_interfaces(self) -> List[str]:
        """Get list of wireless network interfaces"""
        try:
            # Check /proc/net/wireless
            result = await asyncio.create_subprocess_exec(
                'cat', '/proc/net/wireless',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and stdout:
                interfaces = []
                lines = stdout.decode().strip().split('\n')
                for line in lines[2:]:  # Skip header lines
                    if line.strip():
                        interface = line.split(':')[0].strip()
                        if interface:
                            interfaces.append(interface)
                return interfaces
            
            # Fallback: check common wireless interface names
            common_interfaces = ['wlan0', 'wlp2s0', 'wlp3s0', 'wifi0']
            existing_interfaces = []
            
            for interface in common_interfaces:
                if await self._interface_exists(interface):
                    existing_interfaces.append(interface)
            
            return existing_interfaces
            
        except Exception as e:
            self.logger.debug(f"Failed to get wireless interfaces: {e}")
            return []
    
    async def _get_ethernet_interfaces(self) -> List[str]:
        """Get list of ethernet network interfaces"""
        try:
            result = await asyncio.create_subprocess_exec(
                'ls', '/sys/class/net/',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and stdout:
                all_interfaces = stdout.decode().strip().split('\n')
                ethernet_interfaces = []
                
                for interface in all_interfaces:
                    # Skip loopback, wireless, and virtual interfaces
                    if (interface.startswith(('eth', 'enp', 'eno', 'ens')) and 
                        not interface.startswith(('wl', 'lo'))):
                        ethernet_interfaces.append(interface)
                
                return ethernet_interfaces
            
            return []
            
        except Exception as e:
            self.logger.debug(f"Failed to get ethernet interfaces: {e}")
            return []
    
    async def _check_wireless_connection(self, interface: str) -> Dict[str, Any]:
        """Check wireless connection status for an interface"""
        try:
            # Use iwconfig to check connection
            result = await asyncio.create_subprocess_exec(
                'iwconfig', interface,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and stdout:
                output = stdout.decode()
                
                # Check if connected to an access point
                if 'Access Point:' in output and 'Not-Associated' not in output:
                    # Extract SSID
                    ssid_match = re.search(r'ESSID:"([^"]*)"', output)
                    ssid = ssid_match.group(1) if ssid_match else None
                    
                    # Extract signal strength
                    signal_match = re.search(r'Signal level=(-?\d+)', output)
                    signal_strength = signal_match.group(1) if signal_match else None
                    
                    return {
                        "connected": True,
                        "ssid": ssid,
                        "signal_strength": signal_strength
                    }
            
            return {"connected": False, "ssid": None, "signal_strength": None}
            
        except Exception as e:
            self.logger.debug(f"Failed to check wireless connection for {interface}: {e}")
            return {"connected": False, "ssid": None, "signal_strength": None}
    
    async def _is_interface_up(self, interface: str) -> bool:
        """Check if network interface is up"""
        try:
            result = await asyncio.create_subprocess_exec(
                'cat', f'/sys/class/net/{interface}/operstate',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and stdout:
                state = stdout.decode().strip().lower()
                return state == 'up'
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Failed to check interface state for {interface}: {e}")
            return False
    
    async def _get_interface_ip(self, interface: str) -> Optional[str]:
        """Get IP address of network interface"""
        try:
            result = await asyncio.create_subprocess_exec(
                'ip', 'addr', 'show', interface,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and stdout:
                output = stdout.decode()
                # Extract IPv4 address
                ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', output)
                if ip_match:
                    return ip_match.group(1)
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Failed to get IP for interface {interface}: {e}")
            return None
    
    async def _interface_exists(self, interface: str) -> bool:
        """Check if network interface exists"""
        try:
            result = await asyncio.create_subprocess_exec(
                'test', '-d', f'/sys/class/net/{interface}',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            return result.returncode == 0
            
        except Exception:
            return False
    
    async def _is_process_running(self, process_name: str) -> bool:
        """Check if a process is running"""
        try:
            result = await asyncio.create_subprocess_exec(
                'pgrep', process_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            return result.returncode == 0 and stdout.strip()
            
        except Exception as e:
            self.logger.debug(f"Failed to check if {process_name} is running: {e}")
            return False
    
    async def _get_hostapd_config(self) -> Dict[str, Any]:
        """Get hostapd configuration"""
        config = {"ssid": None}
        
        try:
            # Common hostapd config locations
            config_paths = [
                '/etc/hostapd/hostapd.conf',
                '/etc/hostapd.conf',
                '/usr/local/etc/hostapd.conf'
            ]
            
            for config_path in config_paths:
                try:
                    result = await asyncio.create_subprocess_exec(
                        'cat', config_path,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await result.communicate()
                    
                    if result.returncode == 0 and stdout:
                        content = stdout.decode()
                        # Extract SSID
                        ssid_match = re.search(r'^ssid=(.+)$', content, re.MULTILINE)
                        if ssid_match:
                            config["ssid"] = ssid_match.group(1).strip()
                            break
                            
                except Exception:
                    continue
            
        except Exception as e:
            self.logger.debug(f"Failed to get hostapd config: {e}")
        
        return config
    
    async def _get_hotspot_clients_count(self) -> int:
        """Get number of connected hotspot clients"""
        try:
            # Check DHCP lease file
            lease_paths = [
                '/var/lib/dhcp/dhcpd.leases',
                '/var/lib/dhcpcd5/dhcpcd.leases',
                '/tmp/dhcp.leases'
            ]
            
            for lease_path in lease_paths:
                try:
                    result = await asyncio.create_subprocess_exec(
                        'cat', lease_path,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await result.communicate()
                    
                    if result.returncode == 0 and stdout:
                        content = stdout.decode()
                        # Count active leases
                        leases = re.findall(r'lease \d+\.\d+\.\d+\.\d+', content)
                        return len(leases)
                        
                except Exception:
                    continue
            
            return 0
            
        except Exception as e:
            self.logger.debug(f"Failed to get hotspot clients count: {e}")
            return 0


# Global instance
_linux_status_checker: Optional[LinuxStatusChecker] = None


def get_linux_status_checker() -> LinuxStatusChecker:
    """Get Linux status checker singleton"""
    global _linux_status_checker
    if _linux_status_checker is None:
        _linux_status_checker = LinuxStatusChecker()
    return _linux_status_checker
