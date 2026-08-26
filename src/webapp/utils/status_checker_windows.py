"""
Windows-specific network status checker
"""

import asyncio
import subprocess
import socket
import re
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class WindowsStatusChecker:
    """Network status checker for Windows systems"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def get_wifi_status(self) -> Dict[str, Any]:
        """Get WiFi connection status"""
        try:
            # Use netsh to get WiFi status
            result = await asyncio.create_subprocess_exec(
                'netsh', 'wlan', 'show', 'profiles',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                return {
                    "status": "not_available",
                    "connected": False,
                    "ssid": None,
                    "signal_strength": None,
                    "interface": None,
                    "ip_address": None
                }
            
            # Check current WiFi connection
            result = await asyncio.create_subprocess_exec(
                'netsh', 'wlan', 'show', 'interfaces',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and stdout:
                try:
                    output = stdout.decode('utf-8')
                except UnicodeDecodeError:
                    output = stdout.decode('cp1252', errors='ignore')
                
                # Parse WiFi interface information
                wifi_info = self._parse_netsh_wlan_output(output)
                
                if wifi_info.get("connected"):
                    return {
                        "status": "connected",
                        "connected": True,
                        "ssid": wifi_info.get("ssid"),
                        "signal_strength": wifi_info.get("signal_strength"),
                        "interface": wifi_info.get("interface"),
                        "ip_address": await self._get_wifi_ip_address()
                    }
                else:
                    return {
                        "status": "disconnected",
                        "connected": False,
                        "ssid": None,
                        "signal_strength": None,
                        "interface": wifi_info.get("interface"),
                        "ip_address": None
                    }
            
            return {
                "status": "error",
                "connected": False,
                "ssid": None,
                "signal_strength": None,
                "interface": None,
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
            # Use ipconfig to get network configuration
            result = await asyncio.create_subprocess_exec(
                'ipconfig', '/all',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and stdout:
                try:
                    output = stdout.decode('utf-8')
                except UnicodeDecodeError:
                    output = stdout.decode('cp1252', errors='ignore')
                
                # Parse ethernet interfaces
                ethernet_info = self._parse_ipconfig_ethernet(output)
                
                if ethernet_info.get("connected"):
                    return {
                        "status": ethernet_info.get("ip_address", "connected"),
                        "connected": True,
                        "interface": ethernet_info.get("interface"),
                        "ip_address": ethernet_info.get("ip_address")
                    }
                else:
                    return {
                        "status": "not_connected",
                        "connected": False,
                        "interface": None,
                        "ip_address": None
                    }
            
            return {
                "status": "error",
                "connected": False,
                "interface": None,
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
            # Check if mobile hotspot is enabled using netsh
            result = await asyncio.create_subprocess_exec(
                'netsh', 'wlan', 'show', 'hostednetwork',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and stdout:
                try:
                    output = stdout.decode('utf-8')
                except UnicodeDecodeError:
                    output = stdout.decode('cp1252', errors='ignore')
                
                # Parse hosted network information
                hotspot_info = self._parse_netsh_hostednetwork(output)
                
                if hotspot_info.get("status") == "Started":
                    # Get hotspot IP address
                    hotspot_ip = await self._get_hotspot_ip_address()
                    status_text = f"Active + {hotspot_ip}" if hotspot_ip else "Active"
                    
                    return {
                        "status": status_text,
                        "active": True,
                        "ssid": hotspot_info.get("ssid"),
                        "ip_address": hotspot_ip,
                        "clients": hotspot_info.get("clients", 0)
                    }
                else:
                    return {
                        "status": "Disabled",
                        "active": False,
                        "ssid": hotspot_info.get("ssid"),
                        "ip_address": None,
                        "clients": 0
                    }
            
            return {
                "status": "Disabled",
                "active": False,
                "ssid": None,
                "ip_address": None,
                "clients": 0
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
    
    def _parse_netsh_wlan_output(self, output: str) -> Dict[str, Any]:
        """Parse netsh wlan show interfaces output"""
        info = {"connected": False, "interface": None, "ssid": None, "signal_strength": None}
        
        lines = output.split('\n')
        current_interface = None
        
        for line in lines:
            line = line.strip()
            
            if 'Name' in line and 'Wi-Fi' in line:
                current_interface = line.split(':')[-1].strip()
                info["interface"] = current_interface
            
            elif 'State' in line and current_interface:
                state = line.split(':')[-1].strip().lower()
                info["connected"] = state == "connected"
            
            elif 'SSID' in line and current_interface:
                ssid = line.split(':')[-1].strip()
                if ssid and ssid != "":
                    info["ssid"] = ssid
            
            elif 'Signal' in line and current_interface:
                signal_match = re.search(r'(\d+)%', line)
                if signal_match:
                    info["signal_strength"] = signal_match.group(1) + "%"
        
        return info
    
    def _parse_ipconfig_ethernet(self, output: str) -> Dict[str, Any]:
        """Parse ipconfig output for Ethernet interfaces"""
        info = {"connected": False, "interface": None, "ip_address": None}
        
        lines = output.split('\n')
        current_interface = None
        in_ethernet_section = False
        
        for line in lines:
            line = line.strip()
            
            # Ethernet adapter section
            if 'Ethernet adapter' in line and ':' in line:
                current_interface = line.split('adapter')[-1].replace(':', '').strip()
                in_ethernet_section = True
                info["interface"] = current_interface
            
            # Empty line indicates end of section
            elif not line and in_ethernet_section:
                in_ethernet_section = False
                current_interface = None
            
            # IPv4 Address
            elif in_ethernet_section and 'IPv4 Address' in line:
                ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                if ip_match:
                    ip_address = ip_match.group(1)
                    if not ip_address.startswith("127."):  # Skip loopback
                        info["connected"] = True
                        info["ip_address"] = ip_address
                        break
            
            # Connection-specific DNS Suffix (indicates active connection)
            elif in_ethernet_section and 'Connection-specific DNS Suffix' in line:
                suffix = line.split(':')[-1].strip()
                if suffix:  # Has DNS suffix, likely connected
                    if not info["connected"]:  # Only if we haven't found IP yet
                        info["connected"] = True
        
        return info
    
    def _parse_netsh_hostednetwork(self, output: str) -> Dict[str, Any]:
        """Parse netsh wlan show hostednetwork output"""
        info = {"status": "Not started", "ssid": None, "clients": 0}
        
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            
            if 'Status' in line:
                status = line.split(':')[-1].strip()
                info["status"] = status
            
            elif 'SSID name' in line:
                ssid = line.split(':')[-1].strip().strip('"')
                if ssid:
                    info["ssid"] = ssid
            
            elif 'Number of clients' in line:
                clients_match = re.search(r'(\d+)', line)
                if clients_match:
                    info["clients"] = int(clients_match.group(1))
        
        return info
    
    async def _get_wifi_ip_address(self) -> Optional[str]:
        """Get WiFi interface IP address"""
        try:
            # Use netsh to get WiFi interface details
            result = await asyncio.create_subprocess_exec(
                'netsh', 'interface', 'ip', 'show', 'addresses', 'Wi-Fi',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and stdout:
                try:
                    output = stdout.decode('utf-8')
                except UnicodeDecodeError:
                    output = stdout.decode('cp1252', errors='ignore')
                
                # Extract IP address
                ip_match = re.search(r'IP Address:\s*(\d+\.\d+\.\d+\.\d+)', output)
                if ip_match:
                    return ip_match.group(1)
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Failed to get WiFi IP address: {e}")
            return None
    
    async def _get_hotspot_ip_address(self) -> Optional[str]:
        """Get hotspot interface IP address"""
        try:
            # Check common hotspot interface names
            hotspot_interfaces = ["Local Area Connection* 1", "Local Area Connection* 2", "Microsoft Wi-Fi Direct Virtual Adapter"]
            
            for interface in hotspot_interfaces:
                result = await asyncio.create_subprocess_exec(
                    'netsh', 'interface', 'ip', 'show', 'addresses', interface,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate()
                
                if result.returncode == 0 and stdout:
                    try:
                        output = stdout.decode('utf-8')
                    except UnicodeDecodeError:
                        output = stdout.decode('cp1252', errors='ignore')
                    
                    # Extract IP address
                    ip_match = re.search(r'IP Address:\s*(\d+\.\d+\.\d+\.\d+)', output)
                    if ip_match:
                        ip_address = ip_match.group(1)
                        # Check if it's a typical hotspot IP range
                        if ip_address.startswith(("192.168.", "10.", "172.")):
                            return ip_address
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Failed to get hotspot IP address: {e}")
            return None


# Global instance
_windows_status_checker: Optional[WindowsStatusChecker] = None


def get_windows_status_checker() -> WindowsStatusChecker:
    """Get Windows status checker singleton"""
    global _windows_status_checker
    if _windows_status_checker is None:
        _windows_status_checker = WindowsStatusChecker()
    return _windows_status_checker
