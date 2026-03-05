from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `chat_logs` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `user_id` INT NOT NULL,
    `message_content` LONGTEXT NOT NULL,
    `response_content` LONGTEXT NOT NULL,
    `is_flagged` BOOL NOT NULL DEFAULT 0,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY `idx_chat_logs_user_id_8d745e` (`user_id`)
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `chat_logs`;"""


MODELS_STATE = (
    "eJztmm1v2zYQgP+KoU8Z0BWx4sRZvtmJ23rzy9A6a9F1EGiJlglLpCpSaYwu/30kJVki9V"
    "LbcOp40JdWPt5JvIfHO77ku+ETB3r0dQ+GyF4aN63vBgY+5A9ay6uWAYIgkwsBA3NPqoJM"
    "Z05ZCGzGpQvgUchFDqR2iAKGCOZSHHmeEBKbKyLsZqIIo68RtBhxIVvCkDf8/Q8XI+zAR0"
    "jTn8HKWiDoOUpXkSO+LeUWWwdSNsTsjVQUX5tbNvEiH2fKwZotCd5oI8yE1IUYhoBB8XoW"
    "RqL7oneJn6lHcU8zlbiLORsHLkDksZy7WzKwCRb8eG+odNAVX/nVbHe6neuLq841V5E92U"
    "i6T7F7me+xoSQwmRlPsh0wEGtIjBm3BxhS0aUCvNslCMvp5Uw0hLzjOsIUWB3DVJBBzALn"
    "QBR98Gh5ELtMBLh5eVnD7K/e+9t3vfdnXOsX4Q3hwRzH+CRpMuM2ATYDKabGDhAT9dME2D"
    "4/3wIg16oEKNtUgPyLDMZzUIX4+4fppBxizkQD6SCbtf5teYgWJvXLAFrDT/grOu1T+tXL"
    "Yzsb9z7pRG9H0770n1DmhvIt8gV9Tlcky8UqN+2FYA7s1TcQOlahhZikSrfY5Ju+LgEYuJ"
    "KV8Fj4l5SPeypTeaGsSHltUYm4Bj1eTRGft8oKSx+5lbUlZ3RKBeY307y46JrnF1fXl51u"
    "9/L6fFNpik11Jac/fCuqjhKlPy5DGNkr+bxDCs3bnGoe3SqN1mRRPYlCHyBvF4gbg70IJr"
    "F4NICdbQB2qgF2CgC5w06clooEBzjyJcUh7xLANizQzKx/XkAa95M/JtOPsmSoUI1xbzS4"
    "aYl/v+A3g/hX/P8XnFjdtPLmO+KvywMp/W4l/K7Ofo5CtnTAukj/jjMrj9+8jb4G4EYM+f"
    "C1eHiRwVyD7643G2h4Au4ctHgMzqsCtByRbneY0Hz2uqRmyvY2mbJdnSnberAhavEFBXoo"
    "KTl9QjwIcMXeMW+noZxzw+ea5hu8h460/nQ6Upab/aFWvif34/6A45V0uRJiSlVXmTo+Kt"
    "lN/hBpavYTie66kjwKUg9QZnnELYN6lyS4cqqqZV1uFA+nlh9nw/Hgw6w3/lPhLLKmaDGl"
    "dK1Jz660/LB5SevjcPauJX62Pk8nA31DtdGbfTZEn0DEiIXJNx62ebdTcSpSt7chFGgtUL"
    "LDrR9I1fIAA3mMdS/3wZlib53E0YmMbBLytQMbBc6eA6taNgN71IFNOp+N6wqsACnd/lcv"
    "tfI2p7jMepaTUQZDn1d4PjKw7CylbmWgmzarA21LEKIHYK/3g1s0bvCqeCnEFIm1/n6Ay8"
    "wbxCpiH4QrXt6wux/iMvMG8Ys5+ueVko2Ia5Sc/qdNr+ouAGyuJPYwR7wEaC6W97tYrrw8"
    "OczNyX4z+EUyzE0NSCmfSFblVegMPlbAKzE9lTuRui3D4NOs/ip0s2MYTSdvU3X9flSlzH"
    "cIAe/BXpjLbBvO5ZwRtRYecN2di7pq2JRz7e8kmoOk/8N5Q3yQdNR12tN/8tzEHA=="
)
