"""
System Tray Icon

Provides status indication through system tray/menu bar
across Windows, macOS, and Linux.
"""

import logging
from tkinter import Tk, Menu, PhotoImage
import platform

logger = logging.getLogger(__name__)


class SystemTrayIcon:
    """
    Cross-platform system tray icon for WorkSpeak Client.
    
    Shows:
    - Running status (green/gray)
    - Rewrite statistics
    - Quick status menu
    
    Note: Tkinter provides basic cross-platform support.
    For production, use platform-specific implementations.
    """
    
    def __init__(self, on_toggle_rewrite: callable, on_quit: callable):
        self.on_toggle_rewrite = on_toggle_rewrite
        self.on_quit = on_quit
        
        self.root = None
        self.tray = None
        self.running = False
        self.auto_rewrite_enabled = True
    
    def create(self):
        """Create and display tray icon"""
        try:
            # Create hidden Tkinter root
            self.root = Tk()
            self.root.withdraw()
            
            # Create tray menu
            self.tray = Menu(self.root, tearoff=0)
            self.tray.add_command(label="Toggle Auto-Rewrite", 
                                 command=self._toggle_rewrite)
            self.tray.add_command(label="Status", command=self._show_status)
            self.tray.add_separator()
            self.tray.add_command(label="Quit", command=self._quit)
            
            # Platform-specific icon handling
            if platform.system().lower() == "windows":
                self._setup_windows_tray()
            elif platform.system().lower() == "darwin":
                self._setup_macos_tray()
            else:
                self._setup_linux_tray()
            
            self.running = True
            logger.info("System tray icon created")
            
        except Exception as e:
            logger.error(f"Failed to create tray icon: {e}")
    
    def _setup_windows_tray(self):
        """Windows tray setup using win32gui"""
        try:
            import win32gui
            import win32con
            import win32api
            from PIL import Image
            import io
            
            # Create popup menu
            self.hmenu = win32gui.GetSystemMenu(0, False)
            
            # Register window class
            hwnd = win32gui.GetForegroundWindow()
            
            # Create icon
            icon_data = self._get_icon_data()
            icon = win32gui.CreateIconFromBuffer(icon_data)
            
            # Add to taskbar
            self.hicon = win32gui.Shell_NotifyIcon(
                win32con.NIM_ADD,
                (
                    0,
                    icon,
                    "WorkSpeak",
                    "WorkSpeak Client Active",
                    0,
                    0,
                    0,
                    0,
                    hwnd,
                    0
                )
            )
            
        except Exception as e:
            logger.error(f"Windows tray setup error: {e}")
    
    def _setup_macos_tray(self):
        """macOS menu bar setup"""
        try:
            import AppKit
            import Quartz
            
            # Create menu
            menu = AppKit.NSMenu.alloc().init()
            
            # Add items
            toggle_item = AppKit.NSMenuItem.alloc().initWithAction_target_accelerator_(
                b"toggleRewrite:", self._toggle_rewrite, None
            )
            menu.addItem(toggle_item)
            
            quit_item = AppKit.NSMenuItem.alloc().initWithAction_target_accelerator_(
                b"quit:", self._quit, None
            )
            menu.addItem(quit_item)
            
            # Create status item
            self.status_item = AppKit.NSStatusBar.systemStatusBar().statusItemWithLength_(
                AppKit.NSStatusItemLengthVariable
            )
            self.status_item.setMenu_(menu)
            self.status_item.setHighlightMode_(1)
            
        except Exception as e:
            logger.error(f"macOS tray setup error: {e}")
    
    def _setup_linux_tray(self):
        """Linux tray setup (GTK/D-Bus)"""
        try:
            # Try to use Python-gi for GTK3
            try:
                import gi
                gi.require_version('Gtk', '3.0')
                from gi.repository import Gtk, Gio
                
                # Create application menu
                # Implementation would use GTK status icon
                
                logger.info("Linux tray using GTK3")
            except (ImportError, ValueError):
                # Fallback to simple implementation
                logger.warning("GTK3 not available, using fallback")
                
        except Exception as e:
            logger.error(f"Linux tray setup error: {e}")
    
    def _get_icon_data(self) -> bytes:
        """Get icon image data"""
        # In production: load from assets/icon.png
        # For now: return placeholder
        return b"placeholder_icon_data"
    
    def _toggle_rewrite(self):
        """Toggle auto-rewrite on/off"""
        self.auto_rewrite_enabled = not self.auto_rewrite_enabled
        
        if self.on_toggle_rewrite:
            logger.info(f"Auto-rewrite toggled to: {self.auto_rewrite_enabled}")
            self.on_toggle_rewrite(self.auto_rewrite_enabled)
    
    def _show_status(self):
        """Show current status in tray"""
        logger.info(f"Status: auto_rewrite={self.auto_rewrite_enabled}")
        # Show notification or message
        pass
    
    def _quit(self):
        """Quit application"""
        self.running = False
        if self.root:
            self.root.quit()
        if self.on_quit:
            self.on_quit()
    
    def run(self):
        """Run tray loop (blocks)"""
        if self.root:
            self.root.mainloop()
    
    def stop(self):
        """Stop tray"""
        self.running = False
        if self.root:
            self.root.destroy()
