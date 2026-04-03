from __future__ import annotations

from .models import ActionClass, ArtifactStage


_ALLOWED_TRANSITIONS = {
    ArtifactStage.INCIDENT: {ArtifactStage.VERIFICATION},
    ArtifactStage.VERIFICATION: {ArtifactStage.APPROVAL, ArtifactStage.EXECUTION},
    ArtifactStage.APPROVAL: {ArtifactStage.EXECUTION},
    ArtifactStage.EXECUTION: {ArtifactStage.CLOSED},
    ArtifactStage.CLOSED: set(),
}


def allowed_next_stages(current: ArtifactStage, action_class: ActionClass) -> set[ArtifactStage]:
    next_stages = set(_ALLOWED_TRANSITIONS[current])
    if current == ArtifactStage.VERIFICATION and action_class == ActionClass.CLASS1:
        next_stages.discard(ArtifactStage.APPROVAL)
    if current == ArtifactStage.VERIFICATION and action_class == ActionClass.CLASS0:
        next_stages = set()
    return next_stages


def assert_transition(current: ArtifactStage, nxt: ArtifactStage, action_class: ActionClass) -> None:
    if nxt not in allowed_next_stages(current, action_class):
        raise ValueError(f"Illegal transition: {current.value} -> {nxt.value} for {action_class.value}")
