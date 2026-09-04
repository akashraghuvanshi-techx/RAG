"""Security-Aware Access Control and Retrieval Filtering."""

from enum import Enum
from typing import List, Optional, Set, Dict, Any
from pydantic import BaseModel, Field


class ClearanceLevel(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    SECRET = "secret"


CLEARANCE_RANK: Dict[ClearanceLevel, int] = {
    ClearanceLevel.PUBLIC: 1,
    ClearanceLevel.INTERNAL: 2,
    ClearanceLevel.CONFIDENTIAL: 3,
    ClearanceLevel.RESTRICTED: 4,
    ClearanceLevel.SECRET: 5,
}


class UserContext(BaseModel):
    """Context of the user or agent requesting information."""
    user_id: str = Field(default="system_agent", description="User or agent identifier")
    role: str = Field(default="engineer", description="Role: admin, engineer, inspector, auditor, guest")
    clearance: ClearanceLevel = Field(default=ClearanceLevel.CONFIDENTIAL)
    departments: List[str] = Field(default_factory=lambda: ["mechanical", "operations", "safety", "general"])
    allowed_projects: Optional[List[str]] = Field(default=None)

    def is_admin(self) -> bool:
        return self.role.lower() in ("admin", "superadmin", "security_officer")

    def get_allowed_clearance_levels(self) -> List[str]:
        """Returns all clearance level strings allowed for this user."""
        user_rank = CLEARANCE_RANK.get(self.clearance, 1)
        return [
            lvl.value for lvl, rank in CLEARANCE_RANK.items()
            if rank <= user_rank
        ]


def build_access_filter(user: Optional[UserContext]) -> Dict[str, Any]:
    """
    Builds a structured metadata filter dict based on user credentials.
    This filter is pushed directly down to Qdrant and SQLite before candidate retrieval.
    """
    if user is None:
        # Default restricted guest access
        user = UserContext(
            user_id="anonymous",
            role="guest",
            clearance=ClearanceLevel.PUBLIC,
            departments=["general"]
        )

    if user.is_admin():
        # Admin can view all classifications up to their clearance level across all departments
        return {
            "allowed_access_levels": user.get_allowed_clearance_levels(),
            "departments": None,  # No department restriction
            "projects": None,
        }

    return {
        "allowed_access_levels": user.get_allowed_clearance_levels(),
        "departments": user.departments + ["general", "all", ""],
        "projects": user.allowed_projects,
    }
