# Lomas Administration

## Admin authorization and bootstraping

As stated in the [Authentication and Authorization page](../../concepts/auth.md), the identity provider (IdP) handles authentication while the Lomas server handles authorization itself. In order to manage users, an admin must thus be both registered at the IdP and in Lomas and have the Lomas admin role.

Since no users are present in the Lomas admin database at first startup, we provide the bootstrap option. When enabled, a simple authorization header `Authorization: Bearer <bootstrap-credentials>` bypasses the standard auth(z) flow and provides admin role priviledges. The Lomas demo setup script (in `server/lomas_server/administration/scripts/lomas_demo_setup.py`) gives an example of how to use bootstrap credentials to add a first admin user.

__Important__: Only use the bootstrap credentials for bootstraping and make sure to disable bootstrap before adding sensitive datasets to Lomas!

## Admin dashboard

The most convenient way for administrators to manage Lomas is via the admin dashboard. It is setup to work with the IdP to authenticate the user and forwards the access token to the server for every API call, thus enabling admin tasks via a UI. Make sure to log in (button in left menu) before trying out the dashboard features. The home page gives general information about the dashboard as well as the server status while the second page offers admin functionalities.

The dashboard is accessible:

- Local devenv: http://localhost:8501/admin
- Kubernetes deployment: If enabled, the Helm chart notes show the dashboard url.
- Onyxia deployment: Once started, click on the "Open" button. Alternatively, the dashboard url is also shown in the Helm chart notes.

### Deleting bootstrap credentials

Once your first admin user was added to Lomas, make sure to disable bootstrap credentials by clicking the delete bootstrap button on top of admin page.

### Dex integration

If you deployed Lomas for testing with Dex as an IdP, the dashboard automatically adds/removes users to/from Dex. Do not use this in production!

__Note:__ By default, the lifetime of tokens delivered by Dex is set very short to speed up our test runs. Make sure to change the setting (in `devenv/dex.nix`) to larger value when testing the dashboard.

## Scripting Option

If you cannot use the admin dashboard for your admin tasks you can write a python script that sends requests to the server API. Make sure to have a user that can programmatically get a token from your IdP, either via client credentials or device authorization flow. We do not provide an example script at the time being.