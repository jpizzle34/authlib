import time
from .oauth1_server import db, User, Client, Token
from .oauth1_server import (
    TestCase,
    create_authorization_server,
    decode_response
)


class TemporaryCredentialsTest(TestCase):
    def prepare_data(self, use_cache=False):
        create_authorization_server(self.app, use_cache)
        user = User(username='foo')
        db.session.add(user)
        db.session.commit()
        client = Client(
            user_id=user.id,
            client_id='client',
            client_secret='secret',
            default_redirect_uri='https://a.b',
        )
        db.session.add(client)
        db.session.commit()

    def test_temporary_credential_parameters_errors(self):
        self.prepare_data(True)
        url = '/oauth/initiate'

        # case 1
        rv = self.client.post(url)
        data = decode_response(rv.data)
        self.assertEqual(data['error'], 'missing_required_parameter')
        self.assertIn('oauth_consumer_key', data['error_description'])

        # case 2
        rv = self.client.post(url, data={'oauth_consumer_key': 'client'})
        data = decode_response(rv.data)
        self.assertEqual(data['error'], 'missing_required_parameter')
        self.assertIn('oauth_callback', data['error_description'])

        # case 3
        rv = self.client.post(url, data={
            'oauth_consumer_key': 'client',
            'oauth_callback': 'invalid_url'
        })
        data = decode_response(rv.data)
        self.assertEqual(data['error'], 'invalid_request')
        self.assertIn('oauth_callback', data['error_description'])

        # case 4
        rv = self.client.post(url, data={
            'oauth_consumer_key': 'invalid-client',
            'oauth_callback': 'oob'
        })
        data = decode_response(rv.data)
        self.assertEqual(data['error'], 'invalid_client')

        # case 5
        rv = self.client.post(url, data={
            'oauth_consumer_key': 'client',
            'oauth_callback': 'oob'
        })
        data = decode_response(rv.data)
        self.assertEqual(data['error'], 'missing_required_parameter')
        self.assertIn('oauth_timestamp', data['error_description'])

        # case 6
        rv = self.client.post(url, data={
            'oauth_consumer_key': 'client',
            'oauth_callback': 'oob',
            'oauth_timestamp': str(int(time.time()))
        })
        data = decode_response(rv.data)
        self.assertEqual(data['error'], 'missing_required_parameter')
        self.assertIn('oauth_nonce', data['error_description'])

    def test_temporary_credential_signatures_errors(self):
        self.prepare_data(True)
        url = '/oauth/initiate'

        rv = self.client.post(url, data={
            'oauth_consumer_key': 'client',
            'oauth_callback': 'oob',
            'oauth_signature_method': 'PLAINTEXT'
        })
        data = decode_response(rv.data)
        self.assertEqual(data['error'], 'missing_required_parameter')
        self.assertIn('oauth_signature', data['error_description'])

        rv = self.client.post(url, data={
            'oauth_consumer_key': 'client',
            'oauth_callback': 'oob',
            'oauth_timestamp': str(int(time.time())),
            'oauth_nonce': 'a'
        })
        data = decode_response(rv.data)
        self.assertEqual(data['error'], 'missing_required_parameter')
        self.assertIn('oauth_signature_method', data['error_description'])

    def test_plaintext_signature(self):
        self.prepare_data(True)
        url = '/oauth/initiate'

        # case 1: use payload
        rv = self.client.post(url, data={
            'oauth_consumer_key': 'client',
            'oauth_callback': 'oob',
            'oauth_signature_method': 'PLAINTEXT',
            'oauth_signature': 'secret&'
        })
        data = decode_response(rv.data)
        self.assertIn('oauth_token', data)

        # case 2: use header
        auth_header = (
            'OAuth oauth_consumer_key="client",'
            'oauth_signature_method="PLAINTEXT",'
            'oauth_callback="oob",'
            'oauth_signature="secret&"'
        )
        headers = {'Authorization': auth_header}
        rv = self.client.post(url, headers=headers)
        data = decode_response(rv.data)
        self.assertIn('oauth_token', data)
