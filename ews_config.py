"""
ews_config.py
Helper module for saving and loading EWS credentials to .env file
"""

import os
from pathlib import Path
from typing import Optional, Dict


def get_env_path() -> Path:
    """Get the path to .env file"""
    return Path(__file__).parent / ".env"


def load_ews_credentials() -> Dict[str, str]:
    """Load EWS credentials from environment variables"""
    return {
        "email": os.getenv("EWS_EMAIL", ""),
        "password": os.getenv("EWS_PASSWORD", ""),
        "host": os.getenv("EWS_HOST", "")
    }


def save_ews_credentials(email: str, password: str, host: str, agent_name: str = "") -> bool:
    """
    Save EWS credentials to .env file
    
    Args:
        email: EWS email address
        password: EWS password
        host: Exchange server host
        agent_name: Name to use in email signatures (optional)
        
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        env_path = get_env_path()
        
        # Read existing .env content
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        else:
            lines = []
        
        # Update or add EWS  credentials
        updated_lines = []
        found_email = False
        found_password = False
        found_host = False
        found_agent_name = False
        
        for line in lines:
            if line.startswith("EWS_EMAIL="):
                updated_lines.append(f"EWS_EMAIL={email}\n")
                found_email = True
            elif line.startswith("EWS_PASSWORD="):
                updated_lines.append(f"EWS_PASSWORD={password}\n")
                found_password = True
            elif line.startswith("EWS_HOST="):
                updated_lines.append(f"EWS_HOST={host}\n")
                found_host = True
            elif line.startswith("AGENT_USER_NAME=") and agent_name:
                updated_lines.append(f"AGENT_USER_NAME={agent_name}\n")
                found_agent_name = True
            else:
                updated_lines.append(line)
        
        # Add missing entries
        if not found_email:
            # Find EWS section or add at beginning
            insert_idx = 0
            for i, line in enumerate(updated_lines):
                if line.startswith("# EWS Configuration"):
                    insert_idx = i + 1
                    break
            updated_lines.insert(insert_idx, f"EWS_EMAIL={email}\n")
        
        if not found_password:
            insert_idx = 0
            for i, line in enumerate(updated_lines):
                if line.startswith("EWS_EMAIL="):
                    insert_idx = i + 1
                    break
            updated_lines.insert(insert_idx, f"EWS_PASSWORD={password}\n")
        
        if not found_host:
            insert_idx = 0
            for i, line in enumerate(updated_lines):
                if line.startswith("EWS_PASSWORD=") or line.startswith("EWS_EMAIL="):
                    insert_idx = i + 1
            updated_lines.insert(insert_idx, f"EWS_HOST={host}\n")
        
        # Handle agent name if provided
        if agent_name and not found_agent_name:
            insert_idx = 0
            for i, line in enumerate(updated_lines):
                if line.startswith("EWS_HOST=") or line.startswith("EWS_PASSWORD=") or line.startswith("EWS_EMAIL="):
                    insert_idx = i + 1
            updated_lines.insert(insert_idx, f"AGENT_USER_NAME={agent_name}\n")
        
        # Write back to .env
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)
        
        # Update current environment variables
        os.environ["EWS_EMAIL"] = email
        os.environ["EWS_PASSWORD"] = password
        os.environ["EWS_HOST"] = host
        if agent_name:
            os.environ["AGENT_USER_NAME"] = agent_name
        
        return True
        
    except Exception as e:
        print(f"Error saving credentials: {e}")
        return False


def test_ews_connection(email: str, password: str, host: Optional[str] = None) -> tuple[bool, str]:
    """
    Test EWS connection with provided credentials
    
    Args:
        email: EWS email address
        password: EWS password
        host: Optional exchange server host
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        from ews_tools2 import set_credentials, get_unread_batch
        
        # Set credentials
        result = set_credentials(email, password, host)
        
        # Try to fetch unread emails as a connection test
        try:
            emails = get_unread_batch(batch_size=1)
            return True, f"✅ Connection successful! Found inbox ({len(emails)} unread messages)"
        except Exception as e:
            return False, f"❌ Connection failed: {str(e)}"
            
    except Exception as e:
        return False, f"❌ Error testing connection: {str(e)}"
