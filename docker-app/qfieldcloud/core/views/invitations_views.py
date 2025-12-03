from drf_spectacular.utils import extend_schema
from invitations.utils import get_invitation_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from qfieldcloud.core import invitations_utils, permissions_utils
from qfieldcloud.core.serializers import InvitationSerializer


class InviteUserPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return permissions_utils.can_send_invitations(request.user, request.user)


@extend_schema(description="Send an invitation to create a QFieldCloud account")
class InviteUserView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, InviteUserPermission]
    serializer_class = InvitationSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        success, message = invitations_utils.invite_user_by_email(
            serializer.validated_data["email"], request.user
        )

        Invitation = get_invitation_model()
        invite = Invitation.objects.filter(email=serializer.validated_data["email"]).first()

        response_data = {"success": success, "message": message}

        if invite:
            response_data["invite_key"] = invite.key

        status_code = status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST

        return Response(response_data, status=status_code)
