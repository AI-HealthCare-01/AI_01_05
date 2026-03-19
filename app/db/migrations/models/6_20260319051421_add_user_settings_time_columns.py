from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `user_settings` (
    `setting_id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `morning_time` TIME(6) NOT NULL DEFAULT '06:00:00',
    `lunch_time` TIME(6) NOT NULL DEFAULT '11:00:00',
    `evening_time` TIME(6) NOT NULL DEFAULT '17:00:00',
    `bedtime_time` TIME(6) NOT NULL DEFAULT '21:00:00',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `user_id` BIGINT NOT NULL UNIQUE,
    CONSTRAINT `fk_user_set_users_dc0a907c` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `user_settings`;"""


MODELS_STATE = (
    "eJztXWtP3Lga/itoPlFpTgUDFLbfhkt32XJZwbC7WraKTGIGi8RJEw90tOK/Hzt3O3YmHu"
    "aW1FLVFsdPsB+/tt+bnf96nu9AN/o4hCGyn3qft/7rYeBB+h/hSX+rB4KgKGcFBDy4cVVQ"
    "1HmISAhsQksfgRtBWuTAyA5RQJCPaSmeuC4r9G1aEeFxUTTB6PsEWsQfQ/IEQ/rg/hstRt"
    "iBP2CU/Rg8W48Iug7XVOSw3x2XW2QaxGXnmHyJK7Lf9mDZvjvxcFE5mJInH+e1ESasdAwx"
    "DAGB7PUknLDms9al/cx6lLS0qJI0sYRx4COYuKTU3YYc2D5m/NHWRHEHx+y3/G+wu3+4f7"
    "T3af+IVolbkpccviXdK/qeAGMGrka9t/g5ICCpEdNY8PYCw4g1qULeyRMI5eyVIAKFtOEi"
    "hRlhdRxmBQWJheAsiEUP/LBciMeECfjg4KCGsz+HNye/DW+2aa0PrDc+FeZExq/SR4PkGS"
    "O2IJJNDQ0S0+rtJHB3Z6cBgbSWksD4GU8g/Y0EJnOQJ/H32+srOYkliEDkHaYdvHeQTfpb"
    "LorIt82ktYZF1mvWaC+Kvrtl8rYvh3+LvJ5cXB/HLPgRGYfxW+IXHFOO2ZL5+Fya/KzgAd"
    "jPryB0rMoTf+Cr6lYfeQNPLAEYjGOuWI9Z/7JNJAh82m2PjZdsjyk9rt9oiorR+rabUiss"
    "2dZzjMbK3aeKbdNO9MtgsLd3ONjZ+3R0sH94eHC0k29J1Ud1e9Px+a9se+IEefZ+VSaPVo"
    "JV6k9p6WziM6xAPSsmyIMfs+cz1oyU481YMk6Ho7PqrpR3mfWrSteIls6mK8Oq6Mqet4mu"
    "0fnlWbzCTtMVlhVsf1LuWUcfxCWWAUb/CJQ/+VGACHCtuEBDJagA51IOVk/xCpQr7BMYSW"
    "QX/lCssTmgJRzWienZ36N6RSAX4Ivrq1+z6qJ2IChbIWTdt4BE3zpNJ7VC5+KQdctnwzVh"
    "Hdos7YNzjd1pOtYzFonb0fDyD24I2ErLngw4+rPSyhqSv2Trr/PRb1vsx61/rq/OZOtJXI"
    "8tKky3mRDfwv6rBZzShp6VZsRwAzsJnDkHlkeagV3rwKaNL41rBENtTbMEmq1ibsgIrkzL"
    "rNhFPNlVpr/4IURj/BVOY7bPabsBtmU7dWrT3KWv2TyW3zJJyUoLIQzBa27vlAWIdo92Cp"
    "JEiRnengxPqbK5HluS6lDkwh/3JHZk9qhfZ0PatJLl+uM1GpC6U9kYipIp3K8xFM2CuXi2"
    "S7MNRhGdm5bSaadWzSXQtnhBV62lU+0hoC2Yi2YZ1vAs5xlF1qMLxmyvqS4Xvu9CgBWrMg"
    "cU6H2gyGXxq7tTNSf4+Pr6giP4+Fxk8O7y+Oxmezdmm1ZCRLFIhMyacGEokdtaVjmcIVUk"
    "FUQ+Zu3QWgxKIOMSMS6R7lrOiUtkQ4JepwiE057ETEke9OuMFIdWQXCNJgprwFRbhS6jjL"
    "nS2FxJaNONaPGod8ayNkvRkwSzCCKuVkQlB7Rky1tBJGUOS8IYEDN1h9eQ6muWR5dYX7Jc"
    "qgVUxLVTTpskAw3UuUCDaiqQUcW6o4qZ6FTnBrYSnUoiA/OMK49cwLhulqG6QcOYdbt+gh"
    "qvuQkzmjBjQuwldJANWKcVwUa+Qr/OmvfyqksKPN73grBAp2zSX5VYh9+aGv0MoTv/C4wx"
    "+Bsb/PnQSDdMNdE/jbEPniGeQ6Eo44w6sWZ1AkVWPB76YbUcZuI/xjbuoAllbOOODmzFNp"
    "aoZc1VKwnYmFh1iUnGgF00uzUGbFk6F2DIFubUH8KLN4//pqatZALLTVxRiI1joA2OAU5Q"
    "az0Eokg3chWUpWeNmQCr38KMmyDzrIeTsfZJQg7UlpjtCq4YcHyWeazFZI5oJ40HTVg8UJ"
    "N4UOHwMYS0K9ie6tDIgQyTXtpxEOofYudRXfcCQuxoM1TGdPx4vzlrbs6ab3xyFIosqrGi"
    "F4mAzvICF7gVuoFzPdJ4gTd0D+mMs9B4gTs6sOb8vkmsabf/jMtUkOhDxynqy9cb6ILMqz"
    "XLsZvmybSH0bel+xERhj2V55A968/0FdJay3cO3vciCEL7yXqG01c/dHr0Ocs5olRZj6FP"
    "CSsVMHqSnCP55QcEelYEv+tYLGXMYjwIS3cgLiVLXu0qjBnSNQQ5UDs9M0uxAgVh12C0im"
    "yJXbgCViEmgbaIcqBWcrkUZ3Z56dVgU4AZPnk+451Lm84MZdjk4lbREwj0A1c5qpVsLj5O"
    "QOnxQ8t2QSRRw9VcCjBDZrIDPdpT6zuMEPF0fLwCrCVkrtrTS83N9DDrHBRLwYZouUudae"
    "3I0wxm86iWUCsuCM1WhLolobImmACFCVAYP3bPBCh+ooHNfZsNb0kSIhlFjuI7XcPMx164"
    "hzdz0NfjG/Z93mlaLu/X+oRpjaUcMM3CKuVjiGyqWpHrk8oRU0l9tUeYtVk7PFYCmYxSc/"
    "B0Ho1HestUJtEaqjUHaqcbfbeZF6jGCSTq1fH8dOELdKtU1k/qHNSysPc7P9Nn1OeOaVlG"
    "fe7owJr8HpPf0+78nmXaLjcw8EPpZx7TJ/06+yWM66zxuFvSAO3ZzMGMQdLYIDHnYDb+HM"
    "zG8xNNPC+9UbtpvKkEaUkoZNVRJmOEdEJXNUZIRwe2YoTEvpM5lkIRZ9ZD+XroIoxsBLDF"
    "jvzpEFxFGopVGSTGjDZmtDGjc2IlRnRGuNqEZh1aowG9/FlsjOfstDqyn3UT6ssYE6tKDW"
    "wPIEmYquZUQgZoyU7OE7jfhMB9NYH7FQJphx3ZdsIYPMMTr7KZcGwW6NUJZO/u6uvV9V9X"
    "vQqpvcvhxdnnLfb3v/jLWfJT8u+/OEV93irDNemvWwcy9g+V5B+K3D+gkDw5QKLzq71DZU"
    "zHb0kJaOegRWXwQSWgirMdAq6Nxw53d5uslLvqlXLXZMsuP1uWceN4aI57snOYuSebp9QF"
    "UfyNdxmp9T4uHmnukF/zHfLGC90JZ6XxQnd0YCte6GfwDHyp+a9WtcqYNqpZSzktT2Do0R"
    "2ejgzU/TC9CDXaQeWw9wuwp/ORWwUbesXbM3CEmK4/H8EyuKFYSK4G4TPd3vB4PoplcEMx"
    "T7GPH3wQOowk2/eC+EOVmjSrXmGolkSmmpw+A0Hg06Z5EJN3njwbFm/aTA1ReeyMu2cDgR"
    "DJ7qvVoeIUpYH/lpIg+bji/GS0+bI61XeHFkZJez/MUkmUeS8n6TnMljJQSrKen4Mim7ul"
    "LJizzPOdZRYYtKldD2wii65k/F1jOPLpX81YPCm/cFO9q/WiFUHC1OsakdKj5Lb0vvYwMk"
    "fGSzH2itQXTjjqc2AKyVxjNoxuIozJgenr5cDkgyx1Oip5FmEtyx1c2FnjCLrQns8RL0CN"
    "J96EWMzA/jSnjbuzu2i4oqp68qyE6kzPW3I69bJHYznJ1O9OkC4ZXAp9kTfJZiiMgjG45C"
    "v1S1xRsSCTKLlEv3S2tebKpMLppX1xkgg1ymbzD3L6EbQCNmyYgGfZgVxoIw+4cuYlaHFv"
    "TeAf09ds5s5al395dnJ+ObzYPugPBK9/Oa1YuCwaIHdq1XxZ8pYy4SrFWQJvmS6/Nzj8lE"
    "sx+6FObm8pvRdVNZ747Ht+DphKXA5K6nhQy1hbnAVkbiCYmUTtQSoo8TVnQQgfqzypc3uq"
    "yFYemVjUB1wkN81JZuzvt9dXiinLoQQq7zDt4z3d3Ul/y0UR+dY60WMd54ywyrFS8QRpn7"
    "eu2AvEY6WpcqUhtAVihQdShiej8z9jc3FDJdbk4nbCn2AcRR0dWHlmBMJQMx1XgLXzkOji"
    "l7/NcLutTL82txOsQgl6v0NNNuEXwFz5C5TtZU9YyjgGb+jqenN+MlrnBQ95XF/hvSzH/W"
    "f4LsspB+sJdact0F4jeZzxRjb2Rnp+iBlxmW7FUz5Sam0iTqW3LVNn6+18+ryzQ/+8w+CZ"
    "oalx6phUFSu2+6MPMvWLaV78udIJtp+0+eZRa2F7d7eFbMMXOJd8i7j1MH7YQsYfoBN7mH"
    "QZF3FrYXzQRhk3TpVO2N7GqdLRgTXZNyb7Zu2jsTHZN2//BxFkclg="
)
