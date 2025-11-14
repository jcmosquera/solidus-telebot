"""
Input validation functions for wallet addresses and other inputs.
"""
import re
from typing import Tuple

def validate_wallet_address(address: str) -> Tuple[bool, str]:
    """
    Validate wallet address format.
    Returns: (is_valid, error_message)
    """
    if not address:
        return False, "Wallet address cannot be empty"
    
    address = address.strip()
    
    # Check length
    if len(address) < 26 or len(address) > 90:
        return False, "Invalid wallet address length"
    
    # Bitcoin address patterns
    btc_legacy = re.match(r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$', address)
    btc_segwit = re.match(r'^bc1[a-z0-9]{39,59}$', address)
    
    # Ethereum address pattern
    eth_pattern = re.match(r'^0x[a-fA-F0-9]{40}$', address)
    
    # Litecoin address patterns
    ltc_pattern = re.match(r'^[LM3][a-km-zA-HJ-NP-Z1-9]{26,33}$', address)
    
    # Generic cryptocurrency address (alphanumeric)
    generic_pattern = re.match(r'^[a-zA-Z0-9]{26,90}$', address)
    
    if btc_legacy or btc_segwit or eth_pattern or ltc_pattern or generic_pattern:
        return True, ""
    
    return False, "Invalid wallet address format. Please provide a valid cryptocurrency address."

def validate_telegram_username(username: str) -> Tuple[bool, str]:
    """
    Validate Telegram username format.
    Returns: (is_valid, error_message)
    """
    if not username:
        return False, "Username cannot be empty"
    
    # Remove @ if present
    username = username.lstrip('@')
    
    # Telegram username rules: 5-32 characters, alphanumeric + underscore
    if len(username) < 5 or len(username) > 32:
        return False, "Username must be 5-32 characters long"
    
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers, and underscores"
    
    return True, ""

def validate_limit(limit: int, min_val: int = 1, max_val: int = 10000) -> Tuple[bool, str]:
    """
    Validate usage limit value.
    Returns: (is_valid, error_message)
    """
    try:
        limit = int(limit)
        if limit < min_val or limit > max_val:
            return False, f"Limit must be between {min_val} and {max_val}"
        return True, ""
    except (ValueError, TypeError):
        return False, "Limit must be a valid number"
