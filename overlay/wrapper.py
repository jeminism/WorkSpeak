"""
Slack Wrapper Script Generator for WorkSpeak Overlay.
Creates wrapper scripts to launch Slack with CDP debugging enabled.
"""

import os
import subprocess
import logging
from pathlib import Path


logger = logging.getLogger("workspeak.overlay.wrapper")


class SlackWrapperGenerator:
    """Generates wrapper scripts to launch Slack with CDP enabled."""
    
    WRAPPER_SCRIPTS = {
        "linux": """#!/bin/bash
# WorkSpeak CDP Wrapper for Slack
# Launches Slack with Chrome DevTools Protocol enabled

# Find Slack installation
SLACK_PATH=""

# Try common locations
for path in \
    "/usr/bin/slack" \
    "/usr/bin/slack-desktop" \
    "/snap/bin/slack" \
    "/opt/Slack/slack" \
    "$HOME/.linux/slack"; do
    
    if [ -f "$path" ]; then
        SLACK_PATH="$path"
        break
    fi
done

# If not found, try to find in PATH
if [ -z "$SLACK_PATH" ]; then
    SLACK_PATH=$(which slack 2>/dev/null || which slack-desktop 2>/dev/null)
fi

if [ -z "$SLACK_PATH" ] || [ ! -x "$SLACK_PATH" ]; then
    echo "Error: Slack not found"
    echo "Please ensure Slack is installed and in your PATH"
    exit 1
fi

# Launch Slack with CDP enabled
exec "$SLACK_PATH" --inspect=9229 --remote-debugging-port=9229 "$@"
""",
        
        "macos": """#!/bin/bash
# WorkSpeak CDP Wrapper for Slack (macOS)
# Launches Slack with Chrome DevTools Protocol enabled

# Try common macOS locations
SLACK_PATH=""

for path in \
    "/Applications/Slack.app/Contents/MacOS/Slack" \
    "$HOME/Applications/Slack.app/Contents/MacOS/Slack"; do
    
    if [ -f "$path" ]; then
        SLACK_PATH="$path"
        break
    fi
done

if [ -z "$SLACK_PATH" ] || [ ! -x "$SLACK_PATH" ]; then
    echo "Error: Slack not found"
    echo "Please ensure Slack.app is installed in /Applications"
    exit 1
fi

# Launch Slack with CDP enabled
exec "$SLACK_PATH" --inspect=9229 --remote-debugging-port=9229 "$@"
""",
        
        "windows": """@echo off
REM WorkSpeak CDP Wrapper for Slack (Windows)
REM Launches Slack with Chrome DevTools Protocol enabled

REM Try common Windows locations
set "SLACK_PATH="

if exist "%LOCALAPPDATA%\\slack\\slack.exe" set "SLACK_PATH=%LOCALAPPDATA%\\slack\\slack.exe"
if exist "%APPDATA%\\slack\\slack.exe" set "SLACK_PATH=%APPDATA%\\slack\\slack.exe"

if "%SLACK_PATH%"=="" (
    echo Error: Slack not found
    echo Please ensure Slack is installed
    pause
    exit /b 1
)

REM Launch Slack with CDP enabled
start "" "%SLACK_PATH%" --inspect=9229 --remote-debugging-port=9229 %*
"""
    }
    
    @classmethod
    def detect_os(cls):
        """Detect the operating system."""
        import sys
        
        if sys.platform == "win32":
            return "windows"
        elif sys.platform == "darwin":
            return "macos"
        elif sys.platform.startswith("linux"):
            return "linux"
        else:
            return None
    
    @classmethod
    def get_wrapper_script(cls, platform: str = None) -> str:
        """Get wrapper script for specified platform."""
        if platform is None:
            platform = cls.detect_os()
        
        if platform not in cls.WRAPPER_SCRIPTS:
            raise ValueError(f"Unsupported platform: {platform}")
        
        return cls.WRAPPER_SCRIPTS[platform]
    
    @classmethod
    def generate_and_install(cls, script_name: str = "slack-cdp", platform: str = None) -> str:
        """
        Generate and install a wrapper script.
        
        Args:
            script_name: Name for the wrapper script (without extension)
            platform: Platform to generate for (auto-detected if not provided)
        
        Returns:
            Path to the installed script
            
        Raises:
            ValueError: If script cannot be installed
        """
        import sys
        
        if platform is None:
            platform = cls.detect_os()
        
        script_content = cls.get_wrapper_script(platform)
        
        if platform == "linux":
            # Find executable directory
            exe_dirs = [
                Path.home() / "bin",
                Path("/usr/local/bin"),
                Path("/usr/bin")
            ]
            
            for exe_dir in exe_dirs:
                if exe_dir.exists() and os.access(exe_dir, os.W_OK | os.X_OK):
                    script_path = exe_dir / f"{script_name}"
                    
                    # Write script
                    with open(script_path, 'w') as f:
                        f.write(script_content)
                    
                    # Make executable
                    import stat
                    script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
                    
                    return str(script_path)
            
            raise ValueError("Cannot write to any executable directory. Use sudo or create ~/bin/")
        
        elif platform == "macos":
            exe_dir = Path.home() / "bin"
            exe_dir.mkdir(exist_ok=True)
            
            script_path = exe_dir / f"{script_name}"
            
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            import stat
            script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
            
            # Add to PATH if not already
            if str(exe_dir) not in os.environ.get('PATH', ''):
                print(f"Note: Add {exe_dir} to your PATH for easy access")
            
            return str(script_path)
        
        elif platform == "windows":
            # Windows script location
            script_path = Path.home() / f"{script_name}.bat"
            
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            return str(script_path)
        
        return ""
    
    @staticmethod
    def print_usage(platform: str = None):
        """Print usage instructions."""
        if platform is None:
            platform = SlackWrapperGenerator.detect_os()
        
        if platform == "linux":
            print("""
Linux Setup Instructions:
-------------------------
1. Create wrapper script:
   $ python -m overlay.wrapper  # Auto-generates slack-cdp in ~/bin

2. Test the wrapper:
   $ ~/bin/slack-cdp --version

3. Launch Slack with CDP:
   $ ~/bin/slack-cdp

4. Verify CDP is running:
   $ ss -tlnp | grep 9229
   Should show: 127.0.0.1:9229

IMPORTANT: Use slack-cdp instead of slack to launch Slack.
""")
        elif platform == "macos":
            print("""
macOS Setup Instructions:
-------------------------
1. Create wrapper script:
   $ python -m overlay.wrapper  # Auto-generates slack-cdp in ~/bin

2. Test the wrapper:
   $ ~/bin/slack-cdp --version

3. Launch Slack with CDP:
   $ ./bin/slack-cdp

IMPORTANT: Use ./bin/slack-cdp instead of launching Slack from Applications.
""")
        elif platform == "windows":
            print("""
Windows Setup Instructions:
-------------------------
1. Create wrapper batch file:
   $ python -m overlay.wrapper  # Generates slack-cdp.bat in Documents

2. Test the batch file:
   $ slack-cdp.bat --version

3. Launch Slack with CDP:
   $ slack-cdp.bat

IMPORTANT: Use slack-cdp.bat instead of launching Slack from Start menu.
""")
        else:
            print(f"""
Unsupported platform: {platform}
Manual setup required:
Start Slack with: slack --inspect=9229 --remote-debugging-port=9229
""")
