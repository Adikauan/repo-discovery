class MiningFailure(Exception):
    """An allow-listed failure safe to persist or project from the mining pipeline."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)
