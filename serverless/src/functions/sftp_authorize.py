import json
import os

import src.libs.exceptions as ex
import src.libs.log as log
import src.libs.secrets as secrets
from src.libs.beacon import ok, bad_request, server_error

# Get our module logger.
logger = log.setup_custom_logger('disco.service')
service_result = {}


def handler(event, context):
    """Handle Lambda event from AWS Transfer for SFTP server using custom IDP."""

    try:
        logger.info(f"[SENTINELS] EVENT: {event}")
        logger.info(f"[SENTINELS] CONTEXT: {vars(context)}")

        username, server_id = creds_server_user(event)
        logger.info("[SENTINELS] Incoming username {username}, server ID {server_id} sent")

        password = creds_password(event)
        secret = creds_secret(username)
        logger.info("[SENTINELS] User secret retrieved from secrets manager")

        # Validate that password matches what is stored in secrets manager.
        # Only validates if password is passed.
        if password != '':
            check_password(password, secret)
            logger.info("[SENTINELS] User authenticated with password")

        # Validate public SSH key if password not passed.
        else:
            service_result['PublicKeys'] = creds_secret_ssh_keys(secret)
            logger.info("[SENTINELS] User authenticated with SSH public key")

        # If we've got this far then we've either authenticated the user by password or we're using SSH
        # public key auth and we've begun constructing the data response.
        role, policy = creds_secret_role_policy(secret)
        service_result['Role'], service_result['Policy'] = role, policy
        logger.info(f"[SENTINELS] User role and policy discovered: {role}")

        home_directory = creds_secret_home_directory(secret)
        service_result['HomeDirectory'] = home_directory
        logger.info(f"[SENTINELS] User home directory discovered: {home_directory}")

        logger.info(f"[SENTINELS] Completed response data: {json.dumps(service_result)}")
        return ok(service_result)

    except ex.SFTPAuthorizeException as exc:
        logger.info(f"[SENTINELS] Failed SFTP authentication: {exc}")
        return bad_request({'message': exc, 'respData': service_result, 'event': event})

    except Exception as exc:
        logger.info(f"[SENTINELS] Unknown server error: {exc}")
        return server_error({'message': exc, 'respData': service_result, 'event': event})


def creds_server_user(event):
    """Get username and server id from passed parameters."""

    # Ensure event parameters are present.
    if 'pathParameters' not in event or 'headers' not in event:
        raise ex.SFTPAuthorizeException("Event parameters not set")

    # Check for username and server id.
    # Found in 'pathParameters': {'serverId': 's-3288a4617c8f427f9', 'username': 'mlfowler'}
    if 'username' not in event['pathParameters'] or 'serverId' not in event['pathParameters']:
        raise ex.SFTPAuthorizeException("Username and/or Server ID parameters not set")

    # Verify server ID against some value, this template does not verify server ID.
    username = event['pathParameters']['username']
    server_id = event['pathParameters']['serverId']

    if username is None or server_id is None:
        raise ex.SFTPAuthorizeException("Username and/or Server ID parameters are empty")

    return username, server_id


def creds_password(event):
    """Get user password if passed in headers."""

    # Check for password or public SSH key authentication.
    # Found in 'headers': {'Password': 'somepassword'}
    if 'Password' in event['headers']:
        password = event['headers']['Password']
    else:
        password = ''

    return password


def creds_secret(username):
    """Get user secret dictionary in secrets manager."""

    # Lookup user's secret which can contain the password or SSH public keys.
    secret_name = f"{os.environ['STAGE']}/SFTP/core/{username}"
    resp = secrets.get_secret(secret_name)
    if resp is not None:
        secret = json.loads(resp)
    else:
        raise ex.SFTPAuthorizeException("User secret not found in secrets manager")

    return secret


def check_password(password, secret):
    """Check that if password is passed it is the same as stored in secret."""

    if password == '' or password is None:
        return

    # Make sure password passed is the same as in secrets store.
    if 'Password' in secret:
        secret_password = secret['Password']
    else:
        raise ex.SFTPAuthorizeException("Unable to authenticate user, no field match in Secret for password")

    if secret_password != password:
        raise ex.SFTPAuthorizeException("Unable to authenticate user, incoming password does not match stored")


def creds_secret_ssh_keys(secret):
    """Get public SSH keys from secret if no password passed."""

    # SSH Public Key Auth Flow, the incoming password was empty so we are trying ssh auth and
    # need to return the public key data if we have it in secret store.
    if 'PublicKey' not in secret:
        raise ex.SFTPAuthorizeException("Unable to authenticate user, no SSH public keys found")

    return [secret['PublicKey']]


def creds_secret_role_policy(secret):
    """Get role and policy that authenticated user will assume."""

    # If we've got this far then we've either authenticated the user by password or we're using SSH
    # public key auth and we've begun constructing the data response. Check for each key value pair.
    # These are required so set to empty string if missing.
    role = secret['Role'] if 'Role' in secret else ''

    # These are optional so set to empty string if missing.
    policy = secret['Policy'] if 'Policy' in secret else ''

    return role, policy


def creds_secret_home_directory(secret):
    """Get user home directory setting."""

    # if 'HomeDirectoryDetails' in secret:
    #     logger.info("[SENTINELS] Home directory details found, applying setting for virtual folders")
    #     service_result['HomeDirectoryDetails'] = secret['HomeDirectoryDetails']
    #     service_result['HomeDirectoryType'] = "LOGICAL"

    if 'HomeDirectory' not in secret:
        raise ex.SFTPAuthorizeException("Home directory not found for user, must be present")

    return secret['HomeDirectory']
