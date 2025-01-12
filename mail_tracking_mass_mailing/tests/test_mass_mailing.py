# Copyright 2016 Tecnativa - Antonio Espinosa
# Copyright 2017 Tecnativa - Vicent Cubells
# Copyright 2017 Tecnativa - David Vidal
# Copyright 2018 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from unittest import mock

from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT

mock_send_email = "odoo.addons.base.models.ir_mail_server.IrMailServer.send_email"


@tagged("-at_install", "post_install")
class TestMassMailing(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        cls.list = cls.env["mailing.list"].create({"name": "Test mail tracking"})
        cls.list.name = f"{cls.list.name} #{cls.list.id}"
        cls.contact_a = cls.env["mailing.contact"].create(
            {
                "list_ids": [(6, 0, cls.list.ids)],
                "name": "Test contact A",
                "email": "contact_a@example.com",
            }
        )
        cls.mailing = cls.env["mailing.mailing"].create(
            {
                "subject": "Test subject",
                "email_from": "from@example.com",
                "mailing_model_id": cls.env.ref(
                    "mass_mailing.model_mailing_contact"
                ).id,
                "mailing_domain": "[('list_ids', 'in', %d)]" % cls.list.id,
                "contact_list_ids": [(6, False, [cls.list.id])],
                "body_html": "<p>Test email body</p>",
                "reply_to_mode": "new",
            }
        )

    @mute_logger("odoo.addons.mail.models.mail_mail")
    def test_smtp_error(self):
        with mock.patch(mock_send_email) as mock_func:
            mock_func.side_effect = Warning("Mock test error")
            self.mailing.action_send_mail()
            for stat in self.mailing.mailing_trace_ids:
                if stat.mail_mail_id:
                    stat.mail_mail_id.send()
                tracking = self.env["mail.tracking.email"].search(
                    [("mail_id_int", "=", stat.mail_mail_id_int)]
                )
                for track in tracking:
                    self.assertEqual("error", track.state)
                    self.assertEqual("Warning", track.error_type)
                    self.assertEqual("Mock test error", track.error_description)
                self.assertEqual(stat.trace_status, "outgoing")
                self.assertEqual(stat.failure_type, "mail_smtp")
            self.assertTrue(self.contact_a.email_bounced)

    def test_tracking_email_link(self):
        self.mailing.action_send_mail()
        for stat in self.mailing.mailing_trace_ids:
            if stat.mail_mail_id:
                stat.mail_mail_id.send()
            tracking_email = self.env["mail.tracking.email"].search(
                [("mail_id_int", "=", stat.mail_mail_id_int)]
            )
            self.assertTrue(tracking_email)
            self.assertEqual(tracking_email.mass_mailing_id.id, self.mailing.id)
            self.assertEqual(tracking_email.mail_stats_id.id, stat.id)
            self.assertEqual(stat.mail_tracking_id.id, tracking_email.id)
            # And now open the email
            metadata = {
                "ip": "127.0.0.1",
                "user_agent": "Odoo Test/1.0",
                "os_family": "linux",
                "ua_family": "odoo",
            }
            tracking_email.event_create("open", metadata)
            self.assertEqual(stat.trace_status, "open")

    def _tracking_email_bounce(self, event_type, state):
        self.mailing.action_send_mail()
        for stat in self.mailing.mailing_trace_ids:
            if stat.mail_mail_id:
                stat.mail_mail_id.send()
            tracking_email = self.env["mail.tracking.email"].search(
                [("mail_id_int", "=", stat.mail_mail_id_int)]
            )
            # And now mark the email as bounce
            metadata = {
                "bounce_type": "499",
                "bounce_description": "Unable to connect to MX servers",
            }
            tracking_email.event_create(event_type, metadata)
            self.assertEqual(stat.trace_status, "bounce")

    def test_tracking_email_hard_bounce(self):
        self._tracking_email_bounce("hard_bounce", "bounced")

    def test_tracking_email_soft_bounce(self):
        self._tracking_email_bounce("soft_bounce", "soft-bounced")

    def test_tracking_email_reject(self):
        self._tracking_email_bounce("reject", "rejected")

    def test_tracking_email_spam(self):
        self._tracking_email_bounce("spam", "spam")

    def test_contact_tracking_emails(self):
        self._tracking_email_bounce("hard_bounce", "bounced")
        self.assertTrue(self.contact_a.email_bounced)
        self.assertTrue(self.contact_a.email_score < 50.0)
        self.contact_a.email = "other_contact_a@example.com"
        self.assertFalse(self.contact_a.email_bounced)
        self.assertTrue(self.contact_a.email_score == 50.0)
        self.contact_a.email = "contact_a@example.com"
        self.assertTrue(self.contact_a.email_bounced)
        self.assertTrue(self.contact_a.email_score < 50.0)
