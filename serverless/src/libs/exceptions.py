class AwsRegionNotSetException(Exception):
    """Raised when no default AWS region is set in the environment
    variables."""
    pass


class APIGatewayHealthCheckException(Exception):
    """Raised when failure happens in API Gateway health check request."""
    pass


class FromBotException(Exception):
    """Raised when suspected bot is hitting service endpoint."""
    pass
