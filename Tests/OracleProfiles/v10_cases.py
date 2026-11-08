"""Duration initialization cases from the pinned v1.0 original."""

from OracleProfiles.duration_cases import profile_cases


def cases(random_source):
    yield from profile_cases(random_source, 0x49E470, 0x148)
