import boto3
import base64
import os

from botocore.exceptions import ClientError

import src.libs.log as log

# Get our module logger.
logger = log.setup_custom_logger('disco.service')

session = boto3.session.Session()
client = session.client(service_name='secretsmanager', region_name=os.environ['AWS_REGION'])


def get_secret(secret_name):
    """Get the system secret value from secrets store."""

    try:
        secret_value = client.get_secret_value(SecretId=secret_name)

    except ClientError as exc:
        logger.info(f"[SENTINELS] Error talking to secrets manager: {exc}")

        # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
        # Deal with the exception here, and/or rethrow at your discretion.
        if exc.response['Error']['Code'] == 'DecryptionFailureException':
            raise exc

        # An error occurred on the server side.
        # Deal with the exception here, and/or rethrow at your discretion.
        elif exc.response['Error']['Code'] == 'InternalServiceErrorException':
            raise exc

        # You provided an invalid value for a parameter.
        # Deal with the exception here, and/or rethrow at your discretion.
        elif exc.response['Error']['Code'] == 'InvalidParameterException':
            raise exc

        # You provided a parameter value that is not valid for the current state of the resource.
        # Deal with the exception here, and/or rethrow at your discretion.
        elif exc.response['Error']['Code'] == 'InvalidRequestException':
            raise exc

        # We can't find the resource that you asked for.
        # Deal with the exception here, and/or rethrow at your discretion.
        elif exc.response['Error']['Code'] == 'ResourceNotFoundException':
            raise exc

    else:

        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in secret_value:
            logger.info("[SENTINELS] Found secret string for specified secret")
            return secret_value['SecretString']

        else:
            logger.info("[SENTINELS] Found binary secret string for specified secret")
            return base64.b64decode(secret_value['SecretBinary'])
