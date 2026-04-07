def get_pharmacy_id(user):
    """
    Safely extract pharmacy_id from a user object.
    Works for both authenticated PharmacyUser and AnonymousUser.
    Returns string UUID or None.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    # Try pharmacy_id direct UUID field first
    pid = getattr(user, 'pharmacy_id', None)
    if pid:
        return str(pid)
    # Fallback: try the pharmacy property (does a DB lookup)
    pharmacy = getattr(user, 'pharmacy', None)
    if pharmacy:
        return str(pharmacy.id)
    return None
