import traceback
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


def app_exception_handler(exc, context):
    if not isinstance(exc, APIException):
        traceback.print_exc()
        exc = InternalServerException(str(exc))

    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)
    return response


class APIBaseException(APIException):

    def __init__(self, status_code, error_code, error_message, error=None):
        response = {"status": "failed", "code": error_code, "message": error_message}
        if error:
            response['error'] = error
        super().__init__(response, status_code)


class UnauthorizedAccess(APIBaseException):
    """
    UnAuthorized Access Exception if access token is not provided or invalid
    """
    def __init__(self, error=None):
        super(UnauthorizedAccess, self).__init__(status.HTTP_401_UNAUTHORIZED, 1000, 'Unauthorized access', error)


class TokenExpired(APIBaseException):
    """
    TokenExpired class to be raised when the JWT access token is expired
    """
    def __init__(self):
        super(TokenExpired, self).__init__(status.HTTP_401_UNAUTHORIZED, 1001, 'Access token expired')


class UnauthorizedClient(APIBaseException):
    """
    Will be thrown If X-Api-Key not found or Invalid
    """
    def __init__(self):
        super(UnauthorizedClient, self).__init__(status.HTTP_401_UNAUTHORIZED, 1002, 'Unauthorized client')


class ClientSignatureExpired(APIBaseException):
    """
    Will be thrown If X-Api-Key is valid and Expired
    """
    def __init__(self):
        super(ClientSignatureExpired, self).__init__(status.HTTP_401_UNAUTHORIZED, 1003, 'Client signature expired')


class InternalServerException(APIBaseException):
    # Will be thrown if any unexpected error occurred
    def __init__(self, error=None):
        super(InternalServerException, self).__init__(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 1004,
            'Server could not process the request. Please contact support', error
        )


class InvalidParameterException(APIBaseException):
    # Will be thrown if the valid parameters were not provided
    def __init__(self, error=None):
        super(InvalidParameterException, self).__init__(
            status.HTTP_400_BAD_REQUEST, 1005, 'Invalid parameters', error
        )


class InvalidTransactionHash(APIBaseException):
    # Will be thrown if the provided tx_hash is invalid or not related to that specific action
    def __init__(self, error=None):
        super(InvalidTransactionHash, self).__init__(
            status.HTTP_400_BAD_REQUEST, 1006, 'Invalid transaction hash provided', error
        )


class Web3ConnectionFailed(APIBaseException):
    # Will be thrown if web3 connection was failed
    def __init__(self, error=None):
        super(Web3ConnectionFailed, self).__init__(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 1006, 'Failed to connect to web3', error
        )


class TransactionFailed(APIBaseException):
    # Will be thrown when tried to update the failed transaction hash
    def __init__(self, error=None):
        super(TransactionFailed, self).__init__(status.HTTP_400_BAD_REQUEST, 1007, 'Transaction failed', error)


class RandomNotGenerated(APIBaseException):
    # Will be thrown when the Random is not yet generated
    def __init__(self, error=None):
        super(RandomNotGenerated, self).__init__(status.HTTP_400_BAD_REQUEST, 1008,
                                                 'Random number not yet generated to declare the winner', error)


class RandomAlreadyGenerated(APIBaseException):
    # Will be thrown when the Random is already generated, and you are trying to generate again
    def __init__(self, error=None):
        super(RandomAlreadyGenerated, self).__init__(status.HTTP_400_BAD_REQUEST, 1009,
                                                     'Random number already generated', error)


class RandomAlreadyRequested(APIBaseException):
    # Will be thrown when the Random is already requested
    def __init__(self, error=None):
        super(RandomAlreadyRequested, self).__init__(status.HTTP_400_BAD_REQUEST, 1010,
                                                     'Random number already generated', error)


class InvalidUserCredentials(APIBaseException):
    """
    UnAuthorized Access Exception if access token is not provided or invalid
    """
    def __init__(self, error=None):
        super(InvalidUserCredentials, self).__init__(status.HTTP_401_UNAUTHORIZED, 1011, 'Invalid credentials', error)