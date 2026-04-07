from rest_framework.permissions import BasePermission


class IsPharmacist(BasePermission):
    pass



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
    pass
