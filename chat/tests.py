from asgiref.sync import async_to_sync
from django.test import TestCase
from unittest.mock import patch

from users.models import User
from lawyer_profile.models import LawyerProfile
from client_profile.models import ClientProfile
from common.models import LawyerClientRelation
from .models import ChatRoom, Message, MessageReadStatus
from .consumers import ChatConsumer


class ChatConsumerMarkReadTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.index_task_patcher = patch("searchs.signals.index_instance_task.delay")
        cls.delete_task_patcher = patch("searchs.signals.delete_instance_task.delay")
        cls.index_task_patcher.start()
        cls.delete_task_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.index_task_patcher.stop()
        cls.delete_task_patcher.stop()
        super().tearDownClass()

    def setUp(self):
        self.lawyer_user = User.objects.create_user(
            phone_number="09120000000",
            password="pass1234",
            first_name="Law",
            last_name="Yer",
            is_active=True,
        )
        self.client_user = User.objects.create_user(
            phone_number="09120000001",
            password="pass1234",
            first_name="Cli",
            last_name="Ent",
            is_active=True,
        )

        self.lawyer_profile = LawyerProfile.objects.create(user=self.lawyer_user)
        self.client_profile = ClientProfile.objects.create(user=self.client_user)
        self.relation = LawyerClientRelation.objects.create(
            lawyer=self.lawyer_profile,
            client=self.client_profile,
        )
        self.room = ChatRoom.objects.create(relation=self.relation)
        self.message = Message.objects.create(
            room=self.room,
            sender=self.lawyer_user,
            content="hello",
        )

    def _build_consumer(self, acting_user):
        consumer = ChatConsumer()
        consumer.scope = {"user": acting_user}
        return consumer

    def test_mark_messages_read_creates_status_records(self):
        consumer = self._build_consumer(self.client_user)

        created_count = async_to_sync(consumer.mark_messages_read)([self.message.id])

        self.assertEqual(created_count, 1)
        status = MessageReadStatus.objects.get()
        self.assertEqual(status.user, self.client_user)
        self.assertEqual(status.message, self.message)

    def test_mark_messages_read_is_idempotent(self):
        consumer = self._build_consumer(self.client_user)

        async_to_sync(consumer.mark_messages_read)([self.message.id])
        created_again = async_to_sync(consumer.mark_messages_read)([self.message.id])

        self.assertEqual(MessageReadStatus.objects.count(), 1)
        self.assertEqual(created_again, 0)
