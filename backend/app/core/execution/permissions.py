from typing import List

class PolicyEngine:
    """
    Engine to enforce node execution policy security checks.
    """
    @staticmethod
    def is_allowed(required_permissions: List[str], granted_permissions: List[str]) -> bool:
        """
        Validates if granted permissions cover the required permissions.
        Supports wildcards:
        - '*' matches everything.
        - 'prefix:*' matches any 'prefix:xxx' scope.
        """
        for req in required_permissions:
            match = False
            for grt in granted_permissions:
                if grt == "*" or grt == req:
                    match = True
                    break
                if grt.endswith(":*"):
                    prefix = grt[:-2]
                    if req.startswith(prefix + ":"):
                        match = True
                        break
            if not match:
                return False
        return True
