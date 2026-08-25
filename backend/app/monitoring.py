"""Small, dependency-free monitoring primitives for the application data volume."""

from __future__ import annotations

import shutil
from dataclasses import asdict, dataclass
from enum import StrEnum
from os import PathLike
from pathlib import Path


class DiskSpaceState(StrEnum):
    HEALTHY = "healthy"
    LOW = "low"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class DiskSpaceStatus:
    """Disk check result suitable for a health endpoint, audit event, or alert."""

    path: str
    threshold_percent: float
    state: DiskSpaceState
    total_bytes: int | None
    used_bytes: int | None
    free_bytes: int | None
    free_percent: float | None
    detail: str

    @property
    def should_alert(self) -> bool:
        return self.state is not DiskSpaceState.HEALTHY

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def check_disk_space(path: str | PathLike[str], *, threshold_percent: float = 10.0) -> DiskSpaceStatus:
    """Check free capacity for ``path`` without mutating the filesystem.

    ``threshold_percent`` is the minimum acceptable percentage of free space.
    A missing or inaccessible path returns ``unavailable`` rather than raising,
    so callers can alert on monitoring failures too.
    """

    if not 0 <= threshold_percent <= 100:
        raise ValueError("threshold_percent must be between 0 and 100")

    location = Path(path)
    display_path = str(location.absolute())
    try:
        usage = shutil.disk_usage(location)
    except OSError as error:
        return DiskSpaceStatus(
            path=display_path,
            threshold_percent=threshold_percent,
            state=DiskSpaceState.UNAVAILABLE,
            total_bytes=None,
            used_bytes=None,
            free_bytes=None,
            free_percent=None,
            detail=f"Unable to read disk usage: {error.strerror or error.__class__.__name__}",
        )

    free_percent = (usage.free / usage.total * 100) if usage.total else 0.0
    state = DiskSpaceState.LOW if free_percent < threshold_percent else DiskSpaceState.HEALTHY
    return DiskSpaceStatus(
        path=display_path,
        threshold_percent=threshold_percent,
        state=state,
        total_bytes=usage.total,
        used_bytes=usage.used,
        free_bytes=usage.free,
        free_percent=round(free_percent, 2),
        detail=(
            f"{free_percent:.1f}% free is below the {threshold_percent:.1f}% threshold"
            if state is DiskSpaceState.LOW
            else f"{free_percent:.1f}% free"
        ),
    )
