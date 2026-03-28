from .registry import SUBJECT_PROFILES, get_subject_profile

__all__ = ["SUBJECT_PROFILES", "get_subject_profile"]

from autograde.subjects.engineering_labs import EngineeringLabsProfile

from autograde.subjects.communication_vlsi_labs.profile import CommunicationVLSILabsProfile
from autograde.subjects.embedded_systems_labs.profile import EmbeddedSystemsLabsProfile
