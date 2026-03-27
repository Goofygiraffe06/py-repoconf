"""Config schema registry, validators, and command builders."""

from typing import Any, Protocol, TypedDict

try:
    from typing import Unpack
except ImportError:
    from typing_extensions import Unpack


# We define the schema with standard Python identifiers.
# These will be mapped to "section.key" internally (e.g. user_name -> user.name).
class RepoConfigSchema(TypedDict, total=False):
    """
    Schema for allowed configuration keys.
    Uses TypedDict to define expected types and known keys.
    """

    user_name: str
    user_email: str
    core_editor: str
    core_filemode: str
    core_symlinks: str
    repoconf_version: str


class SetCommandSchema(TypedDict):
    """Schema for a validated set command payload."""

    key: str
    value: str


class GetCommandSchema(TypedDict):
    """Schema for a validated get command payload."""

    key: str


class Validator(Protocol):
    """
    Protocol for strict validation before execution.
    Enforces type integrity and mutual exclusivity.

    >>> class DummyValidator:
    ...     def validate(self) -> None:
    ...         pass
    >>> v: Validator = DummyValidator()
    >>> v.validate()
    """

    def validate(self) -> None:
        """
        Validates the state.
        Raises ValueError if validation fails.
        """
        ...


class ConfigArgumentValidator:
    """
    Validates configuration key strings to prevent shell injection
    and ensure they are in the correct format.
    """

    def __init__(self, key: str, value: Any = None):
        self.key = key
        self.value = value

    def validate(self) -> None:
        """
        Validates the key against basic constraints.

        >>> v = ConfigArgumentValidator("user.name")
        >>> v.validate()
        >>> ConfigArgumentValidator("bad name").validate()
        Traceback (most recent call last):
            ...
        ValueError: Invalid characters in configuration key 'bad name'
        """
        if not self.key.replace(".", "").replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"Invalid characters in configuration key '{self.key}'")

        if self.value is not None and not isinstance(
            self.value, (str, int, float, bool)
        ):
            raise ValueError(f"Unsupported value type for key '{self.key}'")


class SetCommandValidator:
    """
    Validator for a set operation ensuring that the keys are part of the schema
    and correctly typed.
    """

    def __init__(self, **kwargs: Unpack[RepoConfigSchema]):
        self.kwargs = kwargs

    def validate(self) -> None:
        """
        Validates the kwargs against the schema.

        >>> v = SetCommandValidator(user_name="test")
        >>> v.validate()
        >>> v2 = SetCommandValidator(unknown_key="test") # type: ignore
        >>> v2.validate()
        Traceback (most recent call last):
            ...
        ValueError: Key 'unknown_key' is not allowed in schema.
        """
        allowed_keys = getattr(RepoConfigSchema, "__annotations__", {})
        for key in self.kwargs:
            if key not in allowed_keys:
                raise ValueError(f"Key '{key}' is not allowed in schema.")


class CommandBuilder:
    """Builder for validated get/set command payloads."""

    # region Builders
    @staticmethod
    def build_set_command(prop: str, value: Any) -> SetCommandSchema:
        """Build a set command payload after validation.

        Args:
            prop: Pythonic property name like ``user_name``.
            value: Value assigned to the property.

        Returns:
            A validated set command payload.
        """
        key = prop.replace("_", ".")
        ConfigArgumentValidator(key=key, value=value).validate()
        return {"key": key, "value": str(value)}

    @staticmethod
    def build_get_command(prop: str) -> GetCommandSchema:
        """Build a get command payload after validation.

        Args:
            prop: Pythonic property name like ``user_name``.

        Returns:
            A validated get command payload.
        """
        key = prop.replace("_", ".")
        ConfigArgumentValidator(key=key).validate()
        return {"key": key}

    # endregion
