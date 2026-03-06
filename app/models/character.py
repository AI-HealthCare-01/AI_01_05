from tortoise import fields, models


class UserCharacter(models.Model):
    id = fields.BigIntField(primary_key=True)
    user = fields.OneToOneField("models.User", related_name="user_character", on_delete=fields.CASCADE)
    character_id = fields.IntField()
    selected_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "user_characters"
