from twisted.internet.defer import inlineCallbacks
from vumi.message import TransportUserMessage

from junebug.amqp import (
    AmqpConnectionError, AmqpFactory, JunebugAMQClient, RoutingKeyError)
from junebug.tests.helpers import FakeAmqpClient, JunebugTestBase


class TestJunebugApi(JunebugTestBase):
    @inlineCallbacks
    def setUp(self):
        yield self.start_server()
        self.message_sender = self.api.message_sender

    def test_amqp_factory_create_client(self):
        '''The amqp factory should create an amqp client with the given
        parameters and of type JunebugAMQClient'''
        factory = AmqpFactory('amqp-spec-0-8.xml', {
            'vhost': '/'}, None, None)
        client = factory.buildProtocol('localhost')
        self.assertTrue(isinstance(client, JunebugAMQClient))
        self.assertEqual(client.vhost, '/')

    @inlineCallbacks
    def test_message_sender_send_message(self):
        '''The message sender should add a message to the correct queue when
        send_message is called'''
        msg = TransportUserMessage.send(
            to_addr='+1234', content='test', transport_name='testtransport')
        yield self.message_sender.send_message(
            msg, routing_key='testtransport')
        [rec_msg] = self.get_dispatched_messages('testtransport')
        self.assertEqual(rec_msg, msg)

    @inlineCallbacks
    def test_message_sender_send_multiple_messages(self):
        '''The message sender should send all messages to their correct queues
        when send_message is called multiple times'''
        msg1 = TransportUserMessage.send(
            to_addr='+1234', content='test1', transport_name='testtransport')
        yield self.message_sender.send_message(
            msg1, routing_key='testtransport')
        msg2 = TransportUserMessage.send(
            to_addr='+1234', content='test2', transport_name='testtransport')
        yield self.message_sender.send_message(
            msg2, routing_key='testtransport')

        [rec_msg1, rec_msg2] = self.get_dispatched_messages('testtransport')
        self.assertEqual(rec_msg1, msg1)
        self.assertEqual(rec_msg2, msg2)

    def test_message_sender_send_message_no_connection(self):
        '''The message sender should raise an error when there is no
        connection to send the message over'''
        self.message_sender.client = None
        msg = TransportUserMessage.send(
            to_addr='+1234', content='test', transport_name='testtransport')
        err = self.assertRaises(
            AmqpConnectionError, self.message_sender.send_message, msg,
            routing_key='testtransport')
        self.assertTrue('Message not sent' in str(err))

    @inlineCallbacks
    def test_message_sender_bad_routing_key(self):
        '''If the routing key is invalid, the message sender should raise an
        error'''
        msg = TransportUserMessage.send(
            to_addr='+1234', content='test', transport_name='testtransport')
        err = yield self.assertFailure(
            self.message_sender.send_message(msg, routing_key='Foo'),
            RoutingKeyError)
        self.assertTrue('Foo' in str(err))
