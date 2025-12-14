"""
Role constants for the MedCode application.

Roles define what actions a user can perform within the system.
Users can have multiple roles assigned.
"""


class Roles:
    # Default role assigned to all new users
    USER = "user"

    # Medical coder - can perform coding tasks
    CODER = "coder"

    # Workflow administrator - manages coding workflows and task assignments
    WORKFLOW_ADMIN = "workflow-admin"

    # User administrator - manages user accounts and role assignments
    USER_ADMIN = "user-admin"

    # Tenant administrator - full administrative access to the tenant
    TENANT_ADMIN = "tenant-admin"


# List of all valid roles for validation
ALL_ROLES = [
    Roles.USER,
    Roles.CODER,
    Roles.WORKFLOW_ADMIN,
    Roles.USER_ADMIN,
    Roles.TENANT_ADMIN,
]

# Default role for new users
DEFAULT_ROLE = Roles.USER
