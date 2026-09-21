from dataclasses import dataclass


@dataclass
class LaunchAutoReviewInput:
    client_type: str
    data_source_paths: list[str]
    additional_info: str | None = None
