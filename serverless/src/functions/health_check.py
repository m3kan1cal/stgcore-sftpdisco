import os

from src.libs.beacon import ok, server_error
import src.libs.exceptions as ex
import src.libs.log as log

# Get our module logger.
logger = log.setup_custom_logger('disco.service')


def handler(event, context):
    """Handle Lambda event from AWS API Gateway."""

    try:
        logger.info(f"REQUEST: {event}")
        logger.info(f"REQUEST: {context}")

        # Clean up the environment variables so we're not exposing
        # any senstive information.
        health_check = dict(os.environ)
        if 'AWS_ACCESS_KEY_ID' in health_check:
            del health_check['AWS_ACCESS_KEY_ID']

        if 'AWS_SECRET_ACCESS_KEY' in health_check:
            del health_check['AWS_SECRET_ACCESS_KEY']

        if 'AWS_SESSION_TOKEN' in health_check:
            del health_check['AWS_SESSION_TOKEN']

        return ok(health_check)

    except ex.APIGatewayHealthCheckException as exc:
        logger.info(f"FAILED: {exc}")
        return server_error({"error": str(exc)})
