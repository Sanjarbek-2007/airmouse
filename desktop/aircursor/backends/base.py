class MouseUnavailable(RuntimeError):
    """Raised when the OS won't let us create a virtual mouse. The message is user-facing."""


class Mouse:
    """Interface of a virtual mouse. Buttons are "left" | "right" | "middle"."""

    live = False

    def move_rel(self, dx: float, dy: float) -> None: ...

    def cancel_motion(self) -> None:
        """Drop any cursor movement that hasn't been delivered yet."""

    def button(self, name: str, down: bool) -> None: ...

    def scroll(self, notches: int, horizontal: bool = False) -> None: ...

    def release_all(self) -> None: ...

    def close(self) -> None: ...


class NullMouse(Mouse):
    """Dry-run mouse: records nothing, does nothing. Detection + UI still work."""
