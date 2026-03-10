from tortoise import fields, models


class Medicine(models.Model):
    item_seq = fields.CharField(max_length=20, primary_key=True)
    item_name = fields.CharField(max_length=255)
    search_keyword = fields.CharField(max_length=255, null=True)
    entp_name = fields.CharField(max_length=100, null=True)
    print_front = fields.CharField(max_length=100, null=True)
    print_back = fields.CharField(max_length=100, null=True)
    drug_shape = fields.CharField(max_length=50, null=True)
    color_class = fields.CharField(max_length=50, null=True)
    efcy_qesitm = fields.TextField(null=True)
    use_method_qesitm = fields.TextField(null=True)
    item_image = fields.CharField(max_length=500, null=True)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "medicines"
        indexes = [("search_keyword",), ("print_front",), ("print_back",)]
