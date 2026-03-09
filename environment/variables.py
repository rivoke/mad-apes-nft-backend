from decouple import config


class EnvironmentVariable:
    """
    @note: This class contains all the access data, common configuration variables
    that used in this application
    """

    # Environment
    BACKEND_ENVIRONMENT = config('BACKEND_ENVIRONMENT', 'MAIN')  # MAIN, LOCAL, DEV, PROD
    BACKEND_PORT = config('PORT', 5000)

    HOST_URL = config('HOST_URL', "http://127.0.0.1:8000")

    DEFAULT_NETWORK = int(config('DEFAULT_NETWORK', 1))

    # Database
    DATABASE_NAME = config('DATABASE_NAME', 'madapenft2')
    DATABASE_HOST = config('DATABASE_HOST', 'localhost')
    DATABASE_PORT = config('DATABASE_PORT', '5432')
    DATABASE_USERNAME = config('DATABASE_USERNAME', 'postgres')
    DATABASE_PASSWORD = config('DATABASE_PASSWORD', 'admin')
    # JWT Access
    JWT_SECRET_KEY = config('JWT_SECRET_KEY')
    # Debug
    DEBUG = config("DEBUG", "True")

    # AWS S3 Configurations
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_ENDPOINT_URL = config('AWS_S3_ENDPOINT_URL')
    AWS_MEDIA_FOLDER = config('AWS_MEDIA_FOLDER', 'madape')

    # NFT

    ACCOUNT_NFT_COLLECTION_ADDRESS = config('ACCOUNT_NFT_COLLECTION_ADDRESS',
                                            '0x267eE01Fc4A7a584E61eC29AfC63dB4C212308F5')
    PRIVATE_KEY = config('PRIVATE_KEY')
    ACCOUNT_NFT_OWNER = config('ACCOUNT_NFT_OWNER', '0x7868933a36Fb7771f5d87c65857F63C9264d28a4')
    LOOTBOX_COLLECTION_ADDRESS = config('LOOTBOX_COLLECTION_ADDRESS', '0xFe3412C8C0938631dAaa879bc41b05D42B48d6Db')
    LOOTBOX_NFT_OWNER = config('LOOTBOX_NFT_OWNER', '0x7868933a36Fb7771f5d87c65857F63C9264d28a4')
    THIRDWEB_API = config('THIRDWEB_API', 'https://api.thirdweb.com/v1/contracts/write')
    THIRDWEB_CLIENT_ID = config('THIRDWEB_CLIENT_ID', '10b55b4e67acd12a01d7a445607fc3c3')
    THIRDWEB_SECRET_ID = config('THIRDWEB_SECRET_ID')

    # web3
    WEB3_PROVIDER_URL = config('WEB3_PROVIDER_URL', 'https://43113.rpc.thirdweb.com/10b55b4e67acd12a01d7a445607fc3c3')
    CHAIN_ID = config('CHAIN_ID', 43113, cast=int)
