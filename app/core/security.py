import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash using bcrypt"""
    try:
        # Securely compare input plain password with the stored hash
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    except Exception:
        # If hash is invalid format or comparison fails, return false
        return False

def get_password_hash(password: str) -> str:
    """Generate a high-security bcrypt hash of the password with salt"""
    # bcrypt generates a random salt automatically
    # Returns the hash as a UTF-8 string to be stored in the database
    return bcrypt.hashpw(
        password.encode('utf-8'), 
        bcrypt.gensalt()
    ).decode('utf-8')
