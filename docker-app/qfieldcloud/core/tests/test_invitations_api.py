import logging

from invitations.utils import get_invitation_model
from rest_framework import status
from rest_framework.test import APITestCase

from qfieldcloud.authentication.models import AuthToken
from qfieldcloud.core.models import Organization, Person

from .utils import set_subscription, setup_subscription_plans

logging.disable(logging.CRITICAL)


class InviteUserAPITestCase(APITestCase):
    def setUp(self):
        setup_subscription_plans()

        self.user = Person.objects.create_user(username="user1", password="abc123")
        self.token = AuthToken.objects.get_or_create(user=self.user)[0]

        self.organization = Organization.objects.create(
            username="org1",
            password="abc123",
            type=Organization.Type.ORGANIZATION,
            organization_owner=self.user,
        )
        set_subscription(self.organization, "default_org")
        self.organization_token = AuthToken.objects.get_or_create(user=self.organization)[0]

        self.invitation_model = get_invitation_model()

    def test_send_invitation(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token.key)
        email = "new.user@example.com"

        response = self.client.post("/api/v1/invitations/", {"email": email})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["success"])

        invite = self.invitation_model.objects.get(email=email)
        self.assertEqual(invite.inviter, self.user)

        self.user.refresh_from_db()
        self.assertEqual(self.user.remaining_invitations, 2)

    def test_invitation_rejects_invalid_email(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token.key)

        response = self.client.post("/api/v1/invitations/", {"email": "invalid"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.json()["success"])
        self.assertFalse(self.invitation_model.objects.exists())

    def test_organization_cannot_send_invitation(self):
        self.client.credentials(
            HTTP_AUTHORIZATION="Token " + self.organization_token.key
        )

        response = self.client.post(
            "/api/v1/invitations/", {"email": "org.invite@example.com"}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(
            self.invitation_model.objects.filter(email="org.invite@example.com").exists()
        )
