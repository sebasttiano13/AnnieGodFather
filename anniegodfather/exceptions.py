class DadClientRegistrationError(Exception):
    """Failed to registr new user"""


class DadClientRegistrationAlreadyExistException(Exception):
    """User already exist exception"""


class AuthManagerError(Exception):
    """General error"""


class AuthLoginUserNotFoundError(Exception):
    """User not found while trying to login in"""


class AuthRefreshAccessTokenError(Exception):
    """Error while trying to refresh access token"""


class AuthBotLoginError(Exception):
    """Error while trying to login in"""
