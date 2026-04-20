"""
Configuration Dialog

Provides UI for configuring the WorkSpeak Client.
"""

import logging
import platform

logger = logging.getLogger(__name__)


class ConfigDialog:
    """
    Cross-platform configuration dialog for WorkSpeak Client.
    
    Features:
    - LLM API key configuration
    - Auto-rewrite toggle
    - Keyboard shortcut configuration
    - Platform selection
    - Log level
    
    Note: Tkinter provides basic cross-platform support.
    For production, use platform-specific implementations.
    """
    
    def __init__(self, config_manager):
        """
        Args:
            config_manager: ConfigManager instance for storing settings
        """
        self.config = config_manager
        self.root = None
    
    def show(self):
        """Show configuration dialog"""
        try:
            from tkinter import Tk, Toplevel, Frame, Label, Entry, Button, \
                                 Checkbutton, IntVar, StringVar, Menu, Scrollbar, \
                                 Listbox, END, messagebox
            import tkinter.ttk as ttk
            
            # Create main dialog window
            self.root = Toplevel()
            self.root.title("WorkSpeak Configuration")
            self.root.geometry("600x500")
            
            # Create main frame
            main_frame = Frame(self.root, padx=20, pady=20)
            main_frame.pack(fill=BOTH, expand=True)
            
            # Section 1: LLM Configuration
            llm_frame = LabelFrame(main_frame, text="LLM Configuration", padx=10, pady=10)
            llm_frame.pack(fill=X, pady=10)
            
            Label(llm_frame, text="API Key:").grid(row=0, column=0, sticky=W, pady=5)
            self.api_key_var = StringVar()
            self.api_key_var.set(self.config.get_llm_api_key())
            Entry(llm_frame, textvariable=self.api_key_var, width=50, show="*").grid(
                row=0, column=1, padx=10
            )
            
            Label(llm_frame, text="Endpoint:").grid(row=1, column=0, sticky=W, pady=5)
            self.endpoint_var = StringVar()
            self.endpoint_var.set(self.config.get_llm_endpoint())
            Entry(llm_frame, textvariable=self.endpoint_var, width=50).grid(
                row=1, column=1, padx=10
            )
            
            Label(llm_frame, text="Model:").grid(row=2, column=0, sticky=W, pady=5)
            self.model_var = StringVar()
            self.model_var.set(self.config.get_llm_model())
            Entry(llm_frame, textvariable=self.model_var, width=50).grid(
                row=2, column=1, padx=10
            )
            
            # Section 2: Behavior
            behavior_frame = LabelFrame(main_frame, text="Behavior", padx=10, pady=10)
            behavior_frame.pack(fill=X, pady=10)
            
            self.auto_rewrite = IntVar()
            self.auto_rewrite.set(self.config.get_auto_rewrite())
            Checkbutton(behavior_frame, text="Auto-rewrite messages", 
                       variable=self.auto_rewrite).pack(anchor=W)
            
            self.show_preview = IntVar()
            self.show_preview.set(self.config.get_preview_enabled())
            Checkbutton(behavior_frame, text="Show preview window", 
                       variable=self.show_preview).pack(anchor=W)
            
            # Section 3: Keyboard Shortcuts
            shortcut_frame = LabelFrame(main_frame, text="Keyboard Shortcut", padx=10, pady=10)
            shortcut_frame.pack(fill=X, pady=10)
            
            Label(shortcut_frame, text="Trigger Key:").pack(anchor=W)
            self.shortcut_var = StringVar()
            self.shortcut_var.set(self.config.get_keyboard_shortcut())
            Entry(shortcut_frame, textvariable=self.shortcut_var, width=30).pack(anchor=W)
            
            # Section 4: Buttons
            button_frame = Frame(main_frame)
            button_frame.pack(pady=20, fill=X)
            
            Button(button_frame, text="Save & Close", 
                  command=self._save).pack(side=LEFT, padx=5)
            Button(button_frame, text="Test Connection", 
                  command=self._test_connection).pack(side=LEFT, padx=5)
            Button(button_frame, text="Cancel", 
                  command=self.root.destroy).pack(side=LEFT, padx=5)
            
            self.root.protocol("WM_DELETE_WINDOW", self._save)
            
        except Exception as e:
            logger.error(f"Config dialog error: {e}")
            messagebox.showerror("Error", f"Failed to open config: {e}")
    
    def _save(self):
        """Save configuration"""
        try:
            self.config.set_llm_config(
                api_key=self.api_key_var.get(),
                endpoint=self.endpoint_var.get(),
                model=self.model_var.get()
            )
            self.config.set_auto_rewrite(bool(self.auto_rewrite.get()))
            self.config.set_preview_enabled(bool(self.show_preview.get()))
            self.config.set_keyboard_shortcut(self.shortcut_var.get())
            
            logger.info("Configuration saved")
            self.root.destroy()
            
        except Exception as e:
            logger.error(f"Save config error: {e}")
            messagebox.showerror("Error", f"Failed to save config: {e}")
    
    def _test_connection(self):
        """Test LLM connection"""
        try:
            import requests
            from tkinter import messagebox
            
            response = requests.post(
                self.endpoint_var.get(),
                headers={
                    "Authorization": f"Bearer {self.api_key_var.get()}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model_var.get(),
                    "messages": [{"role": "user", "content": "test"}]
                },
                timeout=10
            )
            
            if response.status_code == 200:
                messagebox.showinfo("Success", "LLM connection test passed!")
            else:
                messagebox.showerror("Error", 
                                   f"Connection failed: {response.status_code}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Connection test failed: {e}")
    
    def destroy(self):
        """Destroy dialog window"""
        if self.root:
            self.root.destroy()
