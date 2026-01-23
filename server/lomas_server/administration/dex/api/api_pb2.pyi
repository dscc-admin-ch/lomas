from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Client(_message.Message):
    __slots__ = ("id", "secret", "redirect_uris", "trusted_peers", "public", "name", "logo_url")
    ID_FIELD_NUMBER: _ClassVar[int]
    SECRET_FIELD_NUMBER: _ClassVar[int]
    REDIRECT_URIS_FIELD_NUMBER: _ClassVar[int]
    TRUSTED_PEERS_FIELD_NUMBER: _ClassVar[int]
    PUBLIC_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    LOGO_URL_FIELD_NUMBER: _ClassVar[int]
    id: str
    secret: str
    redirect_uris: _containers.RepeatedScalarFieldContainer[str]
    trusted_peers: _containers.RepeatedScalarFieldContainer[str]
    public: bool
    name: str
    logo_url: str
    def __init__(self, id: _Optional[str] = ..., secret: _Optional[str] = ..., redirect_uris: _Optional[_Iterable[str]] = ..., trusted_peers: _Optional[_Iterable[str]] = ..., public: bool = ..., name: _Optional[str] = ..., logo_url: _Optional[str] = ...) -> None: ...

class GetClientReq(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class GetClientResp(_message.Message):
    __slots__ = ("client",)
    CLIENT_FIELD_NUMBER: _ClassVar[int]
    client: Client
    def __init__(self, client: _Optional[_Union[Client, _Mapping]] = ...) -> None: ...

class CreateClientReq(_message.Message):
    __slots__ = ("client",)
    CLIENT_FIELD_NUMBER: _ClassVar[int]
    client: Client
    def __init__(self, client: _Optional[_Union[Client, _Mapping]] = ...) -> None: ...

class CreateClientResp(_message.Message):
    __slots__ = ("already_exists", "client")
    ALREADY_EXISTS_FIELD_NUMBER: _ClassVar[int]
    CLIENT_FIELD_NUMBER: _ClassVar[int]
    already_exists: bool
    client: Client
    def __init__(self, already_exists: bool = ..., client: _Optional[_Union[Client, _Mapping]] = ...) -> None: ...

class DeleteClientReq(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class DeleteClientResp(_message.Message):
    __slots__ = ("not_found",)
    NOT_FOUND_FIELD_NUMBER: _ClassVar[int]
    not_found: bool
    def __init__(self, not_found: bool = ...) -> None: ...

class UpdateClientReq(_message.Message):
    __slots__ = ("id", "redirect_uris", "trusted_peers", "name", "logo_url")
    ID_FIELD_NUMBER: _ClassVar[int]
    REDIRECT_URIS_FIELD_NUMBER: _ClassVar[int]
    TRUSTED_PEERS_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    LOGO_URL_FIELD_NUMBER: _ClassVar[int]
    id: str
    redirect_uris: _containers.RepeatedScalarFieldContainer[str]
    trusted_peers: _containers.RepeatedScalarFieldContainer[str]
    name: str
    logo_url: str
    def __init__(self, id: _Optional[str] = ..., redirect_uris: _Optional[_Iterable[str]] = ..., trusted_peers: _Optional[_Iterable[str]] = ..., name: _Optional[str] = ..., logo_url: _Optional[str] = ...) -> None: ...

class UpdateClientResp(_message.Message):
    __slots__ = ("not_found",)
    NOT_FOUND_FIELD_NUMBER: _ClassVar[int]
    not_found: bool
    def __init__(self, not_found: bool = ...) -> None: ...

class Password(_message.Message):
    __slots__ = ("email", "hash", "username", "user_id")
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    HASH_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    email: str
    hash: bytes
    username: str
    user_id: str
    def __init__(self, email: _Optional[str] = ..., hash: _Optional[bytes] = ..., username: _Optional[str] = ..., user_id: _Optional[str] = ...) -> None: ...

class CreatePasswordReq(_message.Message):
    __slots__ = ("password",)
    PASSWORD_FIELD_NUMBER: _ClassVar[int]
    password: Password
    def __init__(self, password: _Optional[_Union[Password, _Mapping]] = ...) -> None: ...

class CreatePasswordResp(_message.Message):
    __slots__ = ("already_exists",)
    ALREADY_EXISTS_FIELD_NUMBER: _ClassVar[int]
    already_exists: bool
    def __init__(self, already_exists: bool = ...) -> None: ...

class UpdatePasswordReq(_message.Message):
    __slots__ = ("email", "new_hash", "new_username")
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    NEW_HASH_FIELD_NUMBER: _ClassVar[int]
    NEW_USERNAME_FIELD_NUMBER: _ClassVar[int]
    email: str
    new_hash: bytes
    new_username: str
    def __init__(self, email: _Optional[str] = ..., new_hash: _Optional[bytes] = ..., new_username: _Optional[str] = ...) -> None: ...

class UpdatePasswordResp(_message.Message):
    __slots__ = ("not_found",)
    NOT_FOUND_FIELD_NUMBER: _ClassVar[int]
    not_found: bool
    def __init__(self, not_found: bool = ...) -> None: ...

class DeletePasswordReq(_message.Message):
    __slots__ = ("email",)
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    email: str
    def __init__(self, email: _Optional[str] = ...) -> None: ...

class DeletePasswordResp(_message.Message):
    __slots__ = ("not_found",)
    NOT_FOUND_FIELD_NUMBER: _ClassVar[int]
    not_found: bool
    def __init__(self, not_found: bool = ...) -> None: ...

class ListPasswordReq(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ListPasswordResp(_message.Message):
    __slots__ = ("passwords",)
    PASSWORDS_FIELD_NUMBER: _ClassVar[int]
    passwords: _containers.RepeatedCompositeFieldContainer[Password]
    def __init__(self, passwords: _Optional[_Iterable[_Union[Password, _Mapping]]] = ...) -> None: ...

class Connector(_message.Message):
    __slots__ = ("id", "type", "name", "config")
    ID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    id: str
    type: str
    name: str
    config: bytes
    def __init__(self, id: _Optional[str] = ..., type: _Optional[str] = ..., name: _Optional[str] = ..., config: _Optional[bytes] = ...) -> None: ...

class CreateConnectorReq(_message.Message):
    __slots__ = ("connector",)
    CONNECTOR_FIELD_NUMBER: _ClassVar[int]
    connector: Connector
    def __init__(self, connector: _Optional[_Union[Connector, _Mapping]] = ...) -> None: ...

class CreateConnectorResp(_message.Message):
    __slots__ = ("already_exists",)
    ALREADY_EXISTS_FIELD_NUMBER: _ClassVar[int]
    already_exists: bool
    def __init__(self, already_exists: bool = ...) -> None: ...

class UpdateConnectorReq(_message.Message):
    __slots__ = ("id", "new_type", "new_name", "new_config")
    ID_FIELD_NUMBER: _ClassVar[int]
    NEW_TYPE_FIELD_NUMBER: _ClassVar[int]
    NEW_NAME_FIELD_NUMBER: _ClassVar[int]
    NEW_CONFIG_FIELD_NUMBER: _ClassVar[int]
    id: str
    new_type: str
    new_name: str
    new_config: bytes
    def __init__(self, id: _Optional[str] = ..., new_type: _Optional[str] = ..., new_name: _Optional[str] = ..., new_config: _Optional[bytes] = ...) -> None: ...

class UpdateConnectorResp(_message.Message):
    __slots__ = ("not_found",)
    NOT_FOUND_FIELD_NUMBER: _ClassVar[int]
    not_found: bool
    def __init__(self, not_found: bool = ...) -> None: ...

class DeleteConnectorReq(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class DeleteConnectorResp(_message.Message):
    __slots__ = ("not_found",)
    NOT_FOUND_FIELD_NUMBER: _ClassVar[int]
    not_found: bool
    def __init__(self, not_found: bool = ...) -> None: ...

class ListConnectorReq(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ListConnectorResp(_message.Message):
    __slots__ = ("connectors",)
    CONNECTORS_FIELD_NUMBER: _ClassVar[int]
    connectors: _containers.RepeatedCompositeFieldContainer[Connector]
    def __init__(self, connectors: _Optional[_Iterable[_Union[Connector, _Mapping]]] = ...) -> None: ...

class VersionReq(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class VersionResp(_message.Message):
    __slots__ = ("server", "api")
    SERVER_FIELD_NUMBER: _ClassVar[int]
    API_FIELD_NUMBER: _ClassVar[int]
    server: str
    api: int
    def __init__(self, server: _Optional[str] = ..., api: _Optional[int] = ...) -> None: ...

class DiscoveryReq(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DiscoveryResp(_message.Message):
    __slots__ = ("issuer", "authorization_endpoint", "token_endpoint", "jwks_uri", "userinfo_endpoint", "device_authorization_endpoint", "introspection_endpoint", "grant_types_supported", "response_types_supported", "subject_types_supported", "id_token_signing_alg_values_supported", "code_challenge_methods_supported", "scopes_supported", "token_endpoint_auth_methods_supported", "claims_supported")
    ISSUER_FIELD_NUMBER: _ClassVar[int]
    AUTHORIZATION_ENDPOINT_FIELD_NUMBER: _ClassVar[int]
    TOKEN_ENDPOINT_FIELD_NUMBER: _ClassVar[int]
    JWKS_URI_FIELD_NUMBER: _ClassVar[int]
    USERINFO_ENDPOINT_FIELD_NUMBER: _ClassVar[int]
    DEVICE_AUTHORIZATION_ENDPOINT_FIELD_NUMBER: _ClassVar[int]
    INTROSPECTION_ENDPOINT_FIELD_NUMBER: _ClassVar[int]
    GRANT_TYPES_SUPPORTED_FIELD_NUMBER: _ClassVar[int]
    RESPONSE_TYPES_SUPPORTED_FIELD_NUMBER: _ClassVar[int]
    SUBJECT_TYPES_SUPPORTED_FIELD_NUMBER: _ClassVar[int]
    ID_TOKEN_SIGNING_ALG_VALUES_SUPPORTED_FIELD_NUMBER: _ClassVar[int]
    CODE_CHALLENGE_METHODS_SUPPORTED_FIELD_NUMBER: _ClassVar[int]
    SCOPES_SUPPORTED_FIELD_NUMBER: _ClassVar[int]
    TOKEN_ENDPOINT_AUTH_METHODS_SUPPORTED_FIELD_NUMBER: _ClassVar[int]
    CLAIMS_SUPPORTED_FIELD_NUMBER: _ClassVar[int]
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    userinfo_endpoint: str
    device_authorization_endpoint: str
    introspection_endpoint: str
    grant_types_supported: _containers.RepeatedScalarFieldContainer[str]
    response_types_supported: _containers.RepeatedScalarFieldContainer[str]
    subject_types_supported: _containers.RepeatedScalarFieldContainer[str]
    id_token_signing_alg_values_supported: _containers.RepeatedScalarFieldContainer[str]
    code_challenge_methods_supported: _containers.RepeatedScalarFieldContainer[str]
    scopes_supported: _containers.RepeatedScalarFieldContainer[str]
    token_endpoint_auth_methods_supported: _containers.RepeatedScalarFieldContainer[str]
    claims_supported: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, issuer: _Optional[str] = ..., authorization_endpoint: _Optional[str] = ..., token_endpoint: _Optional[str] = ..., jwks_uri: _Optional[str] = ..., userinfo_endpoint: _Optional[str] = ..., device_authorization_endpoint: _Optional[str] = ..., introspection_endpoint: _Optional[str] = ..., grant_types_supported: _Optional[_Iterable[str]] = ..., response_types_supported: _Optional[_Iterable[str]] = ..., subject_types_supported: _Optional[_Iterable[str]] = ..., id_token_signing_alg_values_supported: _Optional[_Iterable[str]] = ..., code_challenge_methods_supported: _Optional[_Iterable[str]] = ..., scopes_supported: _Optional[_Iterable[str]] = ..., token_endpoint_auth_methods_supported: _Optional[_Iterable[str]] = ..., claims_supported: _Optional[_Iterable[str]] = ...) -> None: ...

class RefreshTokenRef(_message.Message):
    __slots__ = ("id", "client_id", "created_at", "last_used")
    ID_FIELD_NUMBER: _ClassVar[int]
    CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    LAST_USED_FIELD_NUMBER: _ClassVar[int]
    id: str
    client_id: str
    created_at: int
    last_used: int
    def __init__(self, id: _Optional[str] = ..., client_id: _Optional[str] = ..., created_at: _Optional[int] = ..., last_used: _Optional[int] = ...) -> None: ...

class ListRefreshReq(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: _Optional[str] = ...) -> None: ...

class ListRefreshResp(_message.Message):
    __slots__ = ("refresh_tokens",)
    REFRESH_TOKENS_FIELD_NUMBER: _ClassVar[int]
    refresh_tokens: _containers.RepeatedCompositeFieldContainer[RefreshTokenRef]
    def __init__(self, refresh_tokens: _Optional[_Iterable[_Union[RefreshTokenRef, _Mapping]]] = ...) -> None: ...

class RevokeRefreshReq(_message.Message):
    __slots__ = ("user_id", "client_id")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    client_id: str
    def __init__(self, user_id: _Optional[str] = ..., client_id: _Optional[str] = ...) -> None: ...

class RevokeRefreshResp(_message.Message):
    __slots__ = ("not_found",)
    NOT_FOUND_FIELD_NUMBER: _ClassVar[int]
    not_found: bool
    def __init__(self, not_found: bool = ...) -> None: ...

class VerifyPasswordReq(_message.Message):
    __slots__ = ("email", "password")
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    PASSWORD_FIELD_NUMBER: _ClassVar[int]
    email: str
    password: str
    def __init__(self, email: _Optional[str] = ..., password: _Optional[str] = ...) -> None: ...

class VerifyPasswordResp(_message.Message):
    __slots__ = ("verified", "not_found")
    VERIFIED_FIELD_NUMBER: _ClassVar[int]
    NOT_FOUND_FIELD_NUMBER: _ClassVar[int]
    verified: bool
    not_found: bool
    def __init__(self, verified: bool = ..., not_found: bool = ...) -> None: ...
