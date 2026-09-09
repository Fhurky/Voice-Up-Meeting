"""Safe transport errors never include source bytes, vectors, paths, or tokens."""


class InferenceError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 422):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code

    def as_dict(self) -> dict:
        return {"detail": {"code": self.code, "message": self.message}}
