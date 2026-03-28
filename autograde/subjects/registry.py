from __future__ import annotations

from autograde.subjects.engineering.profile import EngineeringProfile
from autograde.subjects.engineering_labs.profile import EngineeringLabsProfile
from autograde.subjects.communication_vlsi_labs.profile import CommunicationVLSILabsProfile
from autograde.subjects.embedded_systems_labs.profile import EmbeddedSystemsLabsProfile
from autograde.subjects.humanities.profile import HumanitiesProfile
from autograde.subjects.lab_science.profile import LabScienceProfile
from autograde.subjects.mathematics.profile import MathematicsProfile
from autograde.subjects.programming.profile import ProgrammingProfile


SUBJECT_PROFILES = {
    "programming": ProgrammingProfile(),
    "humanities": HumanitiesProfile(),
    "engineering": EngineeringProfile(),
    "engineering_labs": EngineeringLabsProfile(),
    "ee_labs": EngineeringLabsProfile(),
    "communication_vlsi_labs": CommunicationVLSILabsProfile(),
    "embedded_systems_labs": EmbeddedSystemsLabsProfile(),
    "lab_science": LabScienceProfile(),
    "mathematics": MathematicsProfile(),
}


def get_subject_profile(subject_id: str):
    return SUBJECT_PROFILES.get(subject_id)
