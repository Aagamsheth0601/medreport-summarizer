"""Three specialized LLM stages for a synthetic-report portfolio demo."""


class PipelineError(Exception):
    """An actionable, safe-to-display error without provider payloads."""

    def __init__(self, stage: str, message: str):
        self.stage = stage
        super().__init__(f"{stage}: {message}")
