from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `aerich` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `version` VARCHAR(255) NOT NULL,
    `app` VARCHAR(100) NOT NULL,
    `content` JSON NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `users` (
    `user_id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `nickname` VARCHAR(10) NOT NULL,
    `email` VARCHAR(40),
    `gender` VARCHAR(7) NOT NULL COMMENT 'MALE: MALE\nFEMALE: FEMALE\nUNKNOWN: UNKNOWN' DEFAULT 'UNKNOWN',
    `birthday` DATE,
    `phone_number` VARCHAR(11) NOT NULL UNIQUE,
    `is_active` BOOL NOT NULL DEFAULT 1,
    `is_admin` BOOL NOT NULL DEFAULT 0,
    `last_login` DATETIME(6),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `kakao_id` VARCHAR(255) NOT NULL UNIQUE,
    `terms_agreed` BOOL NOT NULL DEFAULT 0,
    `privacy_agreed` BOOL NOT NULL DEFAULT 0,
    `sensitive_agreed` BOOL NOT NULL DEFAULT 0,
    `marketing_agreed` BOOL NOT NULL DEFAULT 0,
    KEY `idx_users_kakao_i_7551dc` (`kakao_id`)
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "eJztmG1T4jAQgP8KwydvxnOkgnB+o4ondwI3iueNL9MJbSgZ2gSbVGUc//slaaFt+iIwKj"
    "LDF2g3u83uk+1u0peySyzo0L0m9JA5Kh+VXsoYuJBfKCO7pTKYTCK5EDAwcKQqiHQGlHnA"
    "ZFw6BA6FXGRBanpowhDBXIp9xxFCYnJFhO1I5GP04EODERuyEfT4wO09FyNswWdIZ7eTsT"
    "FE0LESriJLzC3lBptOpKyN2alUFLMNDJM4vosj5cmUjQieayPMhNSGGHqAQfF45vnCfeFd"
    "GOcsosDTSCVwMWZjwSHwHRYLd0EGJsGCH/eGygBtMct3rVKtVxsHh9UGV5GezCX11yC8KP"
    "bAUBLo9suvchwwEGhIjBG3R+hR4VIK3vEIeNn0YiYKQu64inAGrIjhTBBBjBLnnSi64Nlw"
    "ILaZSHCtVitg9rd5cXzWvNjhWt9ENIQnc5Dj3XBIC8YE2AikeDWWgBiqbybAyv7+AgC5Vi"
    "5AOZYEyGdkMHgHkxB/Xfa62RBjJgrIK8wDvLWQyXZLDqLs/mtiLaAoohZOu5Q+OHF4O53m"
    "P5Xr8XlPlxQIZbYnnyIfoHPGomQOx7GXXwgGwBw/Ac8yUiNEI3m66SFXc1UJwMCWrETEIr"
    "6wiVxRWdBTzUXKC1uLzzXo+jqLmN7Iai86snM7TMxok9rMD007OKhr+weHjVq1Xq819uf9"
    "Jj1U1Hj09k/RexJZ+nYzwsgcy+slCmncZlOr6ULFtKCWqqUUugA5y0CcG6xEMMzFtQGsLg"
    "Kwmg+wmgLIA7aCspQm2MK+Kym2uUsAmzBFM7L+vIQsX3V/d3vXsmUkoZY7zfPWUUn83uHT"
    "VnAX/N/h0OqoFDdfEn9RHZjRr+fCr6vsB8hjIwtM0/RPOLPs/I3bKMx5sYEMuXBPXHzJZC"
    "7Ad9LstxQ8Ex4cNHgODvISNBuRavc+qfnhfSlZKSuLVMpKfqWsqMmGqME3FOgxo+XohDgQ"
    "4JwTZNxOQTnghh/1ms/xvnem6b3eeWK7qbeV9t296ugtjlfS5UqIJbp6kqnloowz5ZtIZ2"
    "afSHTZneRakDqAMsMhdhbUk7DAZVNNWhbVRnGxafWx3+60LvvNzp8EZ1E1xYgmpVNFunOo"
    "1If5Q0rX7f5ZSdyWbnrdlnqgmuv1b8rCJ+AzYmDyxNM2HvZMPBMlD7keFGgNkHHOLV7IpO"
    "U7LOQ69r08BquHnWmYRxuysmHKFy6sP7FWXNik5XZh17qwofPRuo7BGJDM43/+Vitus4nb"
    "rA/5Psqg5/IOz1cGZn1LKdoZqKbb3YFyJPDQIzCnq8FNG2/xJvFSiCkSe/3VAGeZbxEnEb"
    "vAG/P2hu3VEGeZbxGv+dP/639hXrCw"
)
