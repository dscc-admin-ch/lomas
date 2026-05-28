# Authentication and Authorization

Lomas separates authentication from authorization. Authentications is outsourced to an OIDC identity provider (IdP) that is externally managed while the Lomas server handles authorization itself. Every call to a protected API endpoint follows the same workflow:

1. The client gets a user OIDC access token. The Lomas server is agnostic to how this token is acquired as long as it valid.
2. The client makes a request to a protectd API endpoint using the access token.
3. Authentication: The server uses the access token to authenticate the user. The access token authorizes the server to query the IdP's `userinfo` endpoint and thereby verify the user's identity. Since some IdP providers deliver access token in JWT format, the server can alternatively decode the token and verify it with the IdP's public key (this can be configured in the server's config).
4. Authorization: Once the user's identity is verified, the server can lookup the admin database to verify the user role (ie. admin or not) or consult dataset access and remaining DP budget.
    - Role based access management is used for all endpoints that are used to manage Lomas (ie. "admin" endpoints like adding users, datasets, etc., see `server/lomas_server/routes/routes_admin.py`).
    - User based access is used for user queries made via the Lomas client package (ie. query execution, budget consulting, etc.).

We include Dex with local storage as a mock IdP for testing purposes only. Dex as configured in Lomas is not meant for production use!

## Bootstrap

Because no users are present in the Lomas admin database at first startup, we provide the bootstrap option. When enabled, a simple authorization header `Authorization: Bearer <bootstrap-credentials>` bypasses the standard auth(z) flow and provides admin role priviledges. The Lomas demo setup script (in `server/lomas_server/administration/scripts/lomas_demo_setup.py`) gives an example of how to use bootstrap credentials to add a first admin user.

__Important__: Only use the bootstrap credentials for bootstraping and make sure to disable bootstrap before adding sensitive datasets to Lomas!

## Adding users

Make sure to add users to your IdP before adding them to Lomas. Follow [the guide](../server/administration/users.md) for detailed instruction on how to add a user to Lomas.

## Client package

The Lomas client package acts as a public OIDC client and should be registered as such at your IdP. Two flows are supported by the Lomas client package for getting an access token:

- __Password flow - testing only:__ You can configure the client to use the legacy password flow. Username and credentials are set via environment variables or arguments to the `Client` constructor. This method is practical to use for testing but your IdP will probably (and rightfully so) not allow it in production.
- __Device flow:__ By default, the Lomas client chooses the device flow. It prints out a device verification url embedding a unique user code which the user accesses to approve the device after authenticating themself. This is the prefered method for receiving an access token to pass along to the server.

## Admin dashboard

The admin dashboard acts as a private client and should be registered as such at your IdP. It uses the authorization code flow to get an access token that it forwards to the server for every API request.

__Note if using Dex:__ By default, the lifetime of tokens delivered by Dex is set very short to speed up our test runs. Make sure to change the setting (in `devenv/dex.nix`) to larger value when testing the dashboard.








