from rest_framework.permissions import BasePermission


class IsPharmacist(BasePermission):
    """
    Allows access only to users with role == 'pharmacist' 
    AND who have a linked pharmacy.
    """
    message = "You do not have pharmacist access or no pharmacy is linked to your account."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Check role
        user_role = getattr(request.user, 'role', None)
        if user_role != 'pharmacist':
            return False

        # Safest way to check pharmacy (prevents AttributeError / RelatedObjectDoesNotExist)
        try:
            pharmacy = getattr(request.user, 'pharmacy', None)
            if pharmacy is None:
                # Also check if pharmacy_id exists and is not empty
                if hasattr(request.user, 'pharmacy_id') and request.user.pharmacy_id:
                    return True
                return False
            return True
        except Exception:
            # If any error accessing the relation, deny gracefully
            return False
# Keep your other permission classes (they look fine)
class IsManager(BasePermission):
    """Pharmacist with manager-level access — bulk orders, settings."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['pharmacist', 'admin']
        )


class IsDeliveryPartner(BasePermission):
    """Allow rider role (TiDB ENUM value)."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'rider'
        )


class IsPharmacistOrDelivery(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in ['pharmacist', 'rider']