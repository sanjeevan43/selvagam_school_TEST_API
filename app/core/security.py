import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash using bcrypt"""
    try:
        if not hashed_password:
            return False
            
        # Ensure we have bytes for comparison
        password_bytes = plain_password.encode('utf-8')
        
        # If hash is already bytes, use it, otherwise encode it
        if isinstance(hashed_password, str):
            hash_bytes = hashed_password.encode('utf-8')
        else:
            hash_bytes = hashed_password
            
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """Generate a high-security bcrypt hash of the password with salt"""
    # bcrypt generates a random salt automatically
    # Returns the hash as a UTF-8 string to be stored in the database
    return bcrypt.hashpw(
        password.encode('utf-8'), 
        bcrypt.gensalt()
    ).decode('utf-8')
def generate_default_password(name: str, phone: int) -> str:
    """
    Generate default password: First 4 letters of name + "@" + Last 4 digits of phone
    If name has < 4 chars, use full name.
    """
    phone_str = str(phone)
    if len(phone_str) < 4:
        # This will be caught by the route and turned into an HTTPException if needed,
        # but the request specifically asked to handle it safely and return validation error.
        raise ValueError("Phone number must have at least 4 digits")
    
    # Extract first 4 chars from name
    name_part = name[:4]
    
    # Extract last 4 digits from phone
    phone_part = phone_str[-4:]
    
    return f"{name_part}@{phone_part}"
