class AgentParseError(Exception):
    """Raised when an agent's JSON output cannot be parsed."""

    def __init__(self, agent: str, raw_output: str, original: Exception):
        self.agent = agent
        self.raw_output = raw_output
        self.original = original
        super().__init__(f"{agent} returned invalid JSON: {original}")
