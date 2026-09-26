from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar

from google.protobuf import descriptor as _descriptor, message as _message
from google.protobuf.internal import containers as _containers

DESCRIPTOR: _descriptor.FileDescriptor

class Client(_message.Message):
    __slots__ = ("id", "logo_url", "name", "public", "redirect_uris", "secret", "trusted_peers")
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
    def __init__(
        self,
        id: str | None = ...,
        secret: str | None = ...,
        redirect_uris: _Iterable[str] | None = ...,
        trusted_peers: _Iterable[str] | None = ...,
        public: bool = ...,
        name: str | None = ...,
        logo_url: str | None = ...,
    ) -> None: ...

class GetClientReq(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: str | None = ...) -> None: ...

class GetClientResp(_message.Message):
    __slots__ = ("client",)
    CLIENT_FIELD_NUMBER: _ClassVar[int]
    client: Client
    def __init__(self, client: Client | _Mapping | None = ...) -> None: ...

class CreateClientReq(_message.Message):
    __slots__ = ("client",)
    CLIENT_FIELD_NUMBER: _ClassVar[int]
    client: Client
    def __init__(self, client: Client | _Mapping | None = ...) -> None: ...

class CreateClientResp(_message.Message):
    __slots__ = ("already_exists", "client")
    ALREADY_EXISTS_FIELD_NUMBER: _ClassVar[int]
    CLIENT_FIELD_NUMBER: _ClassVar[int]
    already_exists: bool
    client: Client
    def __init__(self, already_exists: bool = ..., client: Client | _Mapping | None = ...) -> None: ...

class DeleteClientReq(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: str | None = ...) -> None: ...

class DeleteClientResp(_message.Message):
    __slots__ = ("not_found",)
    NOT_FOUND_FIELD_NUMBER: _ClassVar[int]
    not_found: bool
    def __init__(self, not_found: bool = ...) -> None: ...

class UpdateClientReq(_message.Message):
    __slots__ = ("id", "logo_url", "name", "redirect_uris", "trusted_peers")
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
    def __init__(
        self,
        id: str | None = ...,
        redirect_uris: _Iterable[str] | None = ...,
        trusted_peers: _Iterable[str] | None = ...,
        name: str | None = ...,
        logo_url: str | None = ...,
    ) -> None: ...

class UpdateClientResp(_message.Message):
    __slots__ = ("not_found",)
    NOT_FOUND_FIELD_NUMBER: _ClassVar[int]
    not_found: bool
    def __init__(self, not_found: bool = ...) -> None: ...

class Password(_message.Message):
    __slots__ = ("email", "hash", "user_id", "username")
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    HASH_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    email: str
    hash: bytes
    username: str
    user_id: str
    def __init__(
        self,
        email: str | None = ...,
        hash: bytes | None = ...,
        username: str | None = ...,
        user_id: str | None = ...,
    ) -> None: ...

class CreatePasswordReq(_message.Message):
    __slots__ = ("password",)
    PASSWORD_FIELD_NUMBER: _ClassVar[int]
    password: Password
    def __init__(self, password: Password | _Mapping | None = ...) -> None: ...

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
    def __init__(
        self, email: str | None = ..., new_hash: bytes | None = ..., new_username: str | None = ...
    ) -> None: ...

class UpdatePasswordResp(_message.Message):
    __slots__ = ("not_found",)
    NOT_FOUND_FIELD_NUMBER: _ClassVar[int]
    not_found: bool
    def __init__(self, not_found: bool = ...) -> None: ...

class DeletePasswordReq(_message.Message):
    __slots__ = ("email",)
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    email: str
    def __init__(self, email: str | None = ...) -> None: ...

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
    def __init__(self, passwords: _Iterable[Password | _Mapping] | None = ...) -> None: ...

class Connector(_message.Message):
    __slots__ = ("config", "id", "name", "type")
    ID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    id: str
    type: str
    name: str
    config: bytes
    def __init__(
        self, id: str | None = ..., type: str | None = ..., name: str | None = ..., config: bytes | None = ...
    ) -> None: ...

class CreateConnectorReq(_message.Message):
    __slots__ = ("connector",)
    CONNECTOR_FIELD_NUMBER: _ClassVar[int]
    connector: Connector
    def __init__(self, connector: Connector | _Mapping | None = ...) -> None: ...

class CreateConnectorResp(_message.Message):
    __slots__ = ("already_exists",)
    ALREADY_EXISTS_FIELD_NUMBER: _ClassVar[int]
    already_exists: bool
    def __init__(self, already_exists: bool = ...) -> None: ...

class UpdateConnectorReq(_message.Message):
    __slots__ = ("id", "new_config", "new_name", "new_type")
    ID_FIELD_NUMBER: _ClassVar[int]
    NEW_TYPE_FIELD_NUMBER: _ClassVar[int]
    NEW_NAME_FIELD_NUMBER: _ClassVar[int]
    NEW_CONFIG_FIELD_NUMBER: _ClassVar[int]
    id: str
    new_type: str
    new_name: str
    new_config: bytes
    def __init__(
        self,
        id: str | None = ...,
        new_type: str | None = ...,
        new_name: str | None = ...,
        new_config: bytes | None = ...,
    ) -> None: ...

class UpdateConnectorResp(_message.Message):
    __slots__ = ("not_found",)
    NOT_FOUND_FIELD_NUMBER: _ClassVar[int]
    not_found: bool
    def __init__(self, not_found: bool = ...) -> None: ...

class DeleteConnectorReq(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: str | None = ...) -> None: ...

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
    def __init__(self, connectors: _Iterable[Connector | _Mapping] | None = ...) -> None: ...

class VersionReq(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class VersionResp(_message.Message):
    __slots__ = ("api", "server")
    SERVER_FIELD_NUMBER: _ClassVar[int]
    API_FIELD_NUMBER: _ClassVar[int]
    server: str
    api: int
    def __init__(self, server: str | None = ..., api: int | None = ...) -> None: ...

class DiscoveryReq(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DiscoveryResp(_message.Message):
    __slots__ = (
        "authorization_endpoint",
        "claims_supported",
        "code_challenge_methods_supported",
        "device_authorization_endpoint",
        "grant_types_supported",
        "id_token_signing_alg_values_supported",
        "introspection_endpoint",
        "issuer",
        "jwks_uri",
        "response_types_supported",
        "scopes_supported",
        "subject_types_supported",
        "token_endpoint",
        "token_endpoint_auth_methods_supported",
        "userinfo_endpoint",
    )
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
    def __init__(
        self,
        issuer: str | None = ...,
        authorization_endpoint: str | None = ...,
        token_endpoint: str | None = ...,
        jwks_uri: str | None = ...,
        userinfo_endpoint: str | None = ...,
        device_authorization_endpoint: str | None = ...,
        introspection_endpoint: str | None = ...,
        grant_types_supported: _Iterable[str] | None = ...,
        response_types_supported: _Iterable[str] | None = ...,
        subject_types_supported: _Iterable[str] | None = ...,
        id_token_signing_alg_values_supported: _Iterable[str] | None = ...,
        code_challenge_methods_supported: _Iterable[str] | None = ...,
        scopes_supported: _Iterable[str] | None = ...,
        token_endpoint_auth_methods_supported: _Iterable[str] | None = ...,
        claims_supported: _Iterable[str] | None = ...,
    ) -> None: ...

class RefreshTokenRef(_message.Message):
    __slots__ = ("client_id", "created_at", "id", "last_used")
    ID_FIELD_NUMBER: _ClassVar[int]
    CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    LAST_USED_FIELD_NUMBER: _ClassVar[int]
    id: str
    client_id: str
    created_at: int
    last_used: int
    def __init__(
        self,
        id: str | None = ...,
        client_id: str | None = ...,
        created_at: int | None = ...,
        last_used: int | None = ...,
    ) -> None: ...

class ListRefreshReq(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: str | None = ...) -> None: ...

class ListRefreshResp(_message.Message):
    __slots__ = ("refresh_tokens",)
    REFRESH_TOKENS_FIELD_NUMBER: _ClassVar[int]
    refresh_tokens: _containers.RepeatedCompositeFieldContainer[RefreshTokenRef]
    def __init__(self, refresh_tokens: _Iterable[RefreshTokenRef | _Mapping] | None = ...) -> None: ...

class RevokeRefreshReq(_message.Message):
    __slots__ = ("client_id", "user_id")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    client_id: str
    def __init__(self, user_id: str | None = ..., client_id: str | None = ...) -> None: ...

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
    def __init__(self, email: str | None = ..., password: str | None = ...) -> None: ...

class VerifyPasswordResp(_message.Message):
    __slots__ = ("not_found", "verified")
    VERIFIED_FIELD_NUMBER: _ClassVar[int]
    NOT_FOUND_FIELD_NUMBER: _ClassVar[int]
    verified: bool
    not_found: bool
    def __init__(self, verified: bool = ..., not_found: bool = ...) -> None: ...
