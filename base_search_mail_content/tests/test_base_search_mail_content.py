# Copyright 2017 ForgeFlow S.L.
#   (http://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tests.common import TransactionCase


class TestBaseSearchMailContent(TransactionCase):
    def setUp(self):
        super().setUp()
        self.channel_obj = self.env["discuss.channel"]

    def test_base_search_mail_content_1(self):
        res = self.channel_obj.search([("message_content", "ilike", "xxxyyyzzz")])
        self.assertFalse(res, "You have a channel with xxxyyyzzz :O")

    def test_base_search_mail_content_2(self):
        res = self.channel_obj.get_views(
            [[False, "search"]],
            {"load_fields": False, "load_filters": True, "toolbar": True},
        )
        self.assertIn(
            "message_content",
            res["models"][self.channel_obj._name],
            "message_content field was not detected",
        )
