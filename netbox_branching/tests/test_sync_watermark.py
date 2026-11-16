"""
The sync watermark respects commit visibility (F3).

ObjectChange.time is set when a change is saved, not when its transaction commits. A main transaction
that saved before a sync read the change log and committed after it used to be skipped by every later
sync. The watermark now reaches back to the oldest open transaction, and SyncedChange deduplicates the
overlap.
"""

import uuid
from datetime import timedelta
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.db import connections
from django.test import TestCase
from django.utils import timezone

from core.choices import ObjectChangeActionChoices
from netbox_branching.choices import BranchStatusChoices
from netbox_branching.models import Branch, ObjectChange, SyncedChange
from netbox_branching.models.branches import SYNC_WATERMARK_MAX_LOOKBACK


class _OpenTransaction:
    """Another connection holding a transaction open, like a long bulk write in main."""

    def __init__(self):
        self.conn = connections['default'].copy()
        self.conn.ensure_connection()
        self.conn.connection.autocommit = False
        with self.conn.cursor() as cursor:
            cursor.execute('SELECT now()')  # the transaction starts here
            self.started = cursor.fetchone()[0]

    def close(self):
        self.conn.connection.rollback()
        self.conn.close()


class SyncWatermarkTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        branch = Branch(name='Branch 1')
        branch.status = BranchStatusChoices.READY  # Fake provisioning
        branch.save(provision=False)
        cls.site_ct = ContentType.objects.get(app_label='dcim', model='site')

    def setUp(self):
        self.branch = Branch.objects.get(name='Branch 1')

    def _change(self, time):
        change = ObjectChange.objects.create(
            request_id=uuid.uuid4(),
            action=ObjectChangeActionChoices.ACTION_UPDATE,
            changed_object_type=self.site_ct,
            changed_object_id=1,
            user_name='testuser',
        )
        ObjectChange.objects.filter(pk=change.pk).update(time=time)
        return ObjectChange.objects.get(pk=change.pk)

    def test_watermark_without_open_transactions_is_sync_start_minus_margin(self):
        start = timezone.now()
        with patch('netbox_branching.models.branches.connections') as conns:
            conns.__getitem__.return_value.cursor.return_value.__enter__.return_value.fetchone.return_value = [None]
            self.assertEqual(self.branch._sync_watermark(start), start - timedelta(seconds=5))

    def test_watermark_reaches_back_to_the_oldest_open_transaction(self):
        open_tx = _OpenTransaction()
        self.addCleanup(open_tx.close)
        start = timezone.now() + timedelta(seconds=30)
        watermark = self.branch._sync_watermark(start)
        self.assertLessEqual(watermark, open_tx.started - timedelta(seconds=5))

    def test_look_back_is_bounded(self):
        start = timezone.now()
        very_old = start - SYNC_WATERMARK_MAX_LOOKBACK - timedelta(hours=5)
        with patch('netbox_branching.models.branches.connections') as conns:
            conns.__getitem__.return_value.cursor.return_value.__enter__.return_value.fetchone.return_value = [very_old]
            watermark = self.branch._sync_watermark(start)
        self.assertEqual(watermark, start - SYNC_WATERMARK_MAX_LOOKBACK - timedelta(seconds=5))

    def test_change_committed_after_the_sync_read_is_picked_up_next_time(self):
        """
        A change saved (time T) inside a transaction still open when the sync ran, and committed only
        afterwards, must be in the next sync's change set. With last_sync = sync start (> T), it was not.
        """
        open_tx = _OpenTransaction()
        self.addCleanup(open_tx.close)
        saved_at = open_tx.started + timedelta(seconds=1)
        sync_started = saved_at + timedelta(seconds=10)
        # The sync ran here; the change was not visible yet. It records its watermark.
        self.branch.last_sync = sync_started
        self.branch.sync_watermark = self.branch._sync_watermark(sync_started)
        # The transaction commits: the change becomes visible with its save time.
        late = self._change(saved_at)
        self.assertIn(late, self.branch.get_unsynced_changes())

    def test_already_synced_changes_are_skipped(self):
        """The overlap window is re-read; what the previous sync applied is excluded."""
        self.branch.sync_watermark = timezone.now() - timedelta(minutes=1)
        applied = self._change(timezone.now())
        pending = self._change(timezone.now())
        SyncedChange.objects.create(branch=self.branch, change=applied)
        unsynced = set(self.branch.get_unsynced_changes())
        self.assertNotIn(applied, unsynced)
        self.assertIn(pending, unsynced)

    def test_synced_change_is_unique_per_branch(self):
        change = self._change(timezone.now())
        SyncedChange.objects.bulk_create([SyncedChange(branch=self.branch, change=change)], ignore_conflicts=True)
        SyncedChange.objects.bulk_create([SyncedChange(branch=self.branch, change=change)], ignore_conflicts=True)
        self.assertEqual(SyncedChange.objects.filter(branch=self.branch, change=change).count(), 1)
