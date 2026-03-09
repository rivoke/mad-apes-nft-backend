import random
import string
from typing import Optional, List
from web3 import Web3
from common.utils import account_abi, lootbox_abi
from environment.variables import EnvironmentVariable
from ..models import User


def generate_unique_referral_code(length: int = 8) -> str:
    """
    Generate a unique referral code of specified length.
    The code consists of uppercase letters and numbers.
    """
    while True:
        # Generate a random string of uppercase letters and numbers
        chars = string.ascii_uppercase + string.digits
        code = ''.join(random.choice(chars) for _ in range(length))

        # Check if this code already exists
        if not User.objects.filter(referral_code=code).exists():
            return code


def get_user_by_referral_code(code: str, validate: bool = True) -> Optional[User]:
    """
    Get a user by their referral code.
    Returns None if no user is found with the given code.
    
    Args:
        code: The referral code to lookup
        validate: If True, only return active users with valid referral codes
    
    Returns:
        User object or None
    """
    if not code:
        return None

    # Clean up the code
    code = code.strip().upper()

    if validate:
        # Only return active users with referral codes
        return User.objects.filter(
            referral_code=code,
            is_active=True
        ).first()
    else:
        return User.objects.filter(referral_code=code).first()


def validate_referral(new_user: User, referral_code: str) -> tuple[Optional[User], Optional[str]]:
    """
    Validate a referral code for a new user signup.
    Performs security checks to prevent exploitation.
    
    Args:
        new_user: The new user being created
        referral_code: The referral code provided
    
    Returns:
        (referrer_user, error_message) tuple
        - If valid: (User, None)
        - If invalid: (None, "error message")
    """
    if not referral_code:
        return None, None

    # Clean up the code
    referral_code = referral_code.strip().upper()

    # Get referrer
    referrer = get_user_by_referral_code(referral_code, validate=True)

    if not referrer:
        return None, "Invalid or inactive referral code"

    # Security Check 1: Cannot refer yourself
    if new_user.email and referrer.email and new_user.email.lower() == referrer.email.lower():
        return None, "Cannot use your own referral code"

    if new_user.username and referrer.username and new_user.username.lower() == referrer.username.lower():
        return None, "Cannot use your own referral code"

    # Security Check 2: Referrer must be active
    if not referrer.is_active:
        return None, "Referrer account is inactive"

    # Security Check 3: Referrer must have a valid referral code
    if not referrer.referral_code:
        return None, "Invalid referrer"

    # Security Check 4: Check if new user already has a referrer (shouldn't happen, but safety check)
    if new_user.id and new_user.referred_by:
        return None, "User already has a referrer"

    # Security Check 5: Check if user already claimed rewards
    if new_user.id and new_user.referral_rewards_claimed:
        return None, "Referral rewards already claimed"

    return referrer, None


def is_username_available(username: str, exclude_user_id: Optional[int] = None) -> bool:
    """
    Check if a username is available.
    
    Args:
        username: The username to check
        exclude_user_id: Optional user ID to exclude from check (useful for updates)
    
    Returns:
        True if username is available, False otherwise
    """
    if not username:
        return False

    username = username.strip()

    query = User.objects.filter(username__iexact=username)

    # Exclude current user when updating
    if exclude_user_id:
        query = query.exclude(id=exclude_user_id)

    return not query.exists()


def generate_username_suggestions(base_username: str, max_suggestions: int = 5) -> List[str]:
    """
    Generate username suggestions when the requested username is taken.
    
    Args:
        base_username: The original username that was taken
        max_suggestions: Maximum number of suggestions to generate
    
    Returns:
        List of available username suggestions
    """
    if not base_username:
        return []

    base_username = base_username.strip()
    suggestions = []

    # Strategy 1: Add numbers (1-999)
    for i in range(1, 1000):
        if len(suggestions) >= max_suggestions:
            break
        candidate = f"{base_username}{i}"
        if is_username_available(candidate):
            suggestions.append(candidate)

    # Strategy 2: Add underscore and numbers
    if len(suggestions) < max_suggestions:
        for i in range(1, 1000):
            if len(suggestions) >= max_suggestions:
                break
            candidate = f"{base_username}_{i}"
            if is_username_available(candidate):
                suggestions.append(candidate)

    # Strategy 3: Add random suffix (3-4 characters)
    if len(suggestions) < max_suggestions:
        attempts = 0
        while len(suggestions) < max_suggestions and attempts < 100:
            attempts += 1
            # Generate random 3-4 character suffix
            suffix_length = random.randint(3, 4)
            suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=suffix_length))
            candidate = f"{base_username}_{suffix}"
            if is_username_available(candidate):
                suggestions.append(candidate)

    # Strategy 4: Truncate and add numbers (if username is long)
    if len(suggestions) < max_suggestions and len(base_username) > 10:
        truncated = base_username[:10]
        for i in range(1, 100):
            if len(suggestions) >= max_suggestions:
                break
            candidate = f"{truncated}{i}"
            if is_username_available(candidate):
                suggestions.append(candidate)

    return suggestions[:max_suggestions]


def validate_username(username: str, exclude_user_id: Optional[int] = None) -> tuple[bool, Optional[str], List[str]]:
    """
    Validate username and return suggestions if taken.
    
    Args:
        username: The username to validate
        exclude_user_id: Optional user ID to exclude from check (useful for updates)
    
    Returns:
        (is_available: bool, error_message: Optional[str], suggestions: List[str])
    """
    if not username:
        return False, "Username cannot be empty", []

    username = username.strip()

    # Basic validation
    if len(username) < 3:
        return False, "Username must be at least 3 characters long", []

    if len(username) > 150:  # Django's default max_length for username
        return False, "Username must be 150 characters or less", []

    # Check for invalid characters (Django username field allows: @/./+/-/_)
    # But we'll be more restrictive for better UX
    if not username.replace('_', '').replace('.', '').isalnum():
        return False, "Username can only contain letters, numbers, dots, and underscores", []

    # Check availability
    if is_username_available(username, exclude_user_id):
        return True, None, []

    # Username is taken, generate suggestions
    suggestions = generate_username_suggestions(username)

    error_message = f"Username '{username}' is already taken. "
    if suggestions:
        suggestions_str = "', '".join(suggestions)
        error_message += f"Try: '{suggestions_str}'"
    else:
        error_message += "Please try another username."

    return False, error_message, suggestions


w3 = Web3(Web3.HTTPProvider(EnvironmentVariable.WEB3_PROVIDER_URL))
contract = w3.eth.contract(address=EnvironmentVariable.ACCOUNT_NFT_COLLECTION_ADDRESS,
                           abi=account_abi)
lootbox_contract = w3.eth.contract(address=EnvironmentVariable.LOOTBOX_COLLECTION_ADDRESS,
                                   abi=lootbox_abi)
