"""
Writes to a branch while it is being merged or synced (F2).

A write request holds the branch's shared write lock; merge() and sync() switch the status, then
take the lock exclusively before reading the change log. A second database connection plays the
other process (the request, or the merge).
"""

from unittest.mock import patch

from django.db import connections
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from netbox_branching.choices import BranchStatusChoices
from netbox_branching.middleware import BranchMiddleware
from netbox_branching.models import Branch
from netbox_branching.utilities import BRANCH_WRITE_LOCK_NAMESPACE, BranchWriteLockTimeout


class _OtherConnection:
    """A second connection to the test database: another process taking or probing the lock."""

    def __init__(self):
        self.conn = connections['default'].copy()
        self.conn.ensure_connection()

    def scalar(self, sql, params=()):
        with self.conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()[0]

    def close(self):
        self.conn.close()


class BranchWriteLockTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        branch = Branch(name='Branch 1')
        branch.status = BranchStatusChoices.READY  # Fake provisioning
        branch.save(provision=False)

    def setUp(self):
        self.branch = Branch.objects.get(name='Branch 1')
        self.other = _OtherConnection()
        self.addCleanup(self.other.close)

    def _key(self):
        return (BRANCH_WRITE_LOCK_NAMESPACE, self.branch.pk)

    def _api_write(self):
        return RequestFactory().post(
            '/api/dcim/sites/',
            data='{"name": "x"}',
            content_type='application/json',
            headers={'x-netbox-branch': self.branch.schema_id},
        )

    def test_write_request_holds_the_lock_until_its_response(self):
        """While a write request runs, a merge cannot take the lock; it is free once the request returns."""
        seen = {}

        def view(request):
            seen['exclusive_free'] = self.other.scalar('SELECT pg_try_advisory_lock(%s, %s)', self._key())
            return HttpResponse(status=201)

        response = BranchMiddleware(view)(self._api_write())
        self.assertEqual(response.status_code, 201)
        self.assertIs(seen['exclusive_free'], False, 'the write request must hold the shared lock')
        self.assertIs(self.other.scalar('SELECT pg_try_advisory_lock(%s, %s)', self._key()), True)
        self.other.scalar('SELECT pg_advisory_unlock(%s, %s)', self._key())

    def test_read_request_does_not_take_the_lock(self):
        """A GET neither takes nor waits for the write lock."""
        self.other.scalar('SELECT pg_advisory_lock(%s, %s)', self._key())
        self.addCleanup(self.other.scalar, 'SELECT pg_advisory_unlock(%s, %s)', self._key())
        request = RequestFactory().get('/api/dcim/sites/', headers={'x-netbox-branch': self.branch.schema_id})
        response = BranchMiddleware(lambda r: HttpResponse())(request)
        self.assertEqual(response.status_code, 200)

    @override_settings(LOGIN_REQUIRED=False)
    def test_write_refused_while_an_operation_holds_the_lock(self):
        """A merge or sync reading the changes holds the lock exclusively: a write gets a retryable 503."""
        self.other.scalar('SELECT pg_advisory_lock(%s, %s)', self._key())
        self.addCleanup(self.other.scalar, 'SELECT pg_advisory_unlock(%s, %s)', self._key())
        response = self.client.post(
            reverse('dcim-api:site-list'),
            data={'name': 'x'},
            content_type='application/json',
            headers={'x-netbox-branch': self.branch.schema_id},
        )
        self.assertEqual(response.status_code, 503)
        self.assertIs(response.json()['retryable'], True)

    def test_status_is_rechecked_under_the_lock(self):
        """A write that read READY just before a merge switched the status is refused, and releases the lock."""
        Branch.objects.filter(pk=self.branch.pk).update(status=BranchStatusChoices.MERGING)
        stale = Branch.objects.get(pk=self.branch.pk)
        stale.status = BranchStatusChoices.READY  # what get_active_branch() saw a moment earlier
        with patch('netbox_branching.middleware.get_active_branch', return_value=stale):
            response = BranchMiddleware(lambda r: self.fail('the view must not run'))(self._api_write())
        self.assertEqual(response.status_code, 503)
        self.assertIs(self.other.scalar('SELECT pg_try_advisory_lock(%s, %s)', self._key()), True)
        self.other.scalar('SELECT pg_advisory_unlock(%s, %s)', self._key())

    def test_merge_gives_up_if_in_flight_writes_do_not_finish(self):
        """A write still holding the lock after write_drain_timeout makes the merge fail; the branch is READY again."""
        from netbox_branching.models import branches

        real = branches.get_plugin_config

        def config(plugin, name, *args, **kwargs):
            return 1 if name == 'write_drain_timeout' else real(plugin, name, *args, **kwargs)

        self.other.scalar('SELECT pg_advisory_lock_shared(%s, %s)', self._key())
        self.addCleanup(self.other.scalar, 'SELECT pg_advisory_unlock_shared(%s, %s)', self._key())
        with patch.object(branches, 'get_plugin_config', side_effect=config), self.assertRaises(BranchWriteLockTimeout):
            self.branch.merge(user=None)
        self.assertEqual(Branch.objects.get(pk=self.branch.pk).status, BranchStatusChoices.READY)

    def test_merge_reads_changes_after_switching_status_and_taking_the_lock(self):
        """
        The change log is read with the branch already MERGING and the write lock held exclusively, so no
        write can commit to the branch after it was read. It used to be read first (F2).
        """
        seen = {}

        def fake_locked(branch, user, commit, logger):
            seen['status'] = Branch.objects.get(pk=branch.pk).status
            seen['shared_free'] = self.other.scalar('SELECT pg_try_advisory_lock_shared(%s, %s)', self._key())

        with patch.object(Branch, '_merge_locked', fake_locked):
            self.branch.merge(user=None)
        self.assertEqual(seen['status'], BranchStatusChoices.MERGING)
        self.assertIs(seen['shared_free'], False, 'no write may take the lock while the merge reads')
        # Released after the merge.
        self.assertIs(self.other.scalar('SELECT pg_try_advisory_lock(%s, %s)', self._key()), True)
        self.other.scalar('SELECT pg_advisory_unlock(%s, %s)', self._key())

    def test_sync_reads_changes_after_switching_status_and_taking_the_lock(self):
        """Same ordering for sync()."""
        seen = {}

        def fake_locked(branch, user, commit, logger):
            seen['status'] = Branch.objects.get(pk=branch.pk).status
            seen['shared_free'] = self.other.scalar('SELECT pg_try_advisory_lock_shared(%s, %s)', self._key())

        with (
            patch.object(Branch, '_sync_locked', fake_locked),
            patch.object(Branch, 'is_stale', False),
        ):
            self.branch.sync(user=None)
        self.assertEqual(seen['status'], BranchStatusChoices.SYNCING)
        self.assertIs(seen['shared_free'], False)
