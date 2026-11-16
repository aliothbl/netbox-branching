"""
Sync commits on two connections (F15), and main's changes during a sync must reach ChangeDiff (F4).

sync() writes main's changes to the branch schema on the branch connection, and its bookkeeping
(SyncedChange, ChangeDiff, the watermark) on the default connection. The two commits are not atomic:
if the default one is lost after the branch one, the next sync reads the same changes again and
replays them onto a branch which already holds them. That replay must converge to the same state.
"""

import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import DEFAULT_DB_ALIAS, DatabaseError, connections
from django.test import RequestFactory
from django.urls import reverse

from dcim.models import Region, Site
from netbox.context_managers import event_tracking
from netbox_branching.choices import BranchStatusChoices
from netbox_branching.models import Branch, ChangeDiff
from netbox_branching.tests.utils import FastTeardownTransactionTestCase, provision_branch
from netbox_branching.utilities import activate_branch

User = get_user_model()


class SyncReplayTestCase(FastTeardownTransactionTestCase):
    serialized_rollback = True

    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        request = RequestFactory().get(reverse('home'))
        request.id = uuid.uuid4()
        request.user = self.user
        self.request = request

    def tearDown(self):
        for branch in Branch.objects.all():
            if hasattr(connections._connections, branch.connection_name):
                connections[branch.connection_name].close()

    def _branch_state(self, branch):
        with activate_branch(branch):
            return (
                sorted(Site.objects.values_list('pk', 'name', 'description')),
                sorted(Region.objects.values_list('pk', 'name', 'parent_id')),
            )

    def test_sync_survives_a_lost_default_commit(self):
        with event_tracking(self.request):
            to_update = Site.objects.create(name='Update', slug='update')
            to_delete = Site.objects.create(name='Delete', slug='delete')
            parent = Region.objects.create(name='Parent', slug='parent')
        branch = provision_branch(user=self.user)

        with event_tracking(self.request):
            Site.objects.create(name='Created', slug='created')
            Region.objects.create(name='Child', slug='child', parent=parent)  # MPTT create
            to_update.description = 'updated in main'
            to_update.save()
            to_delete.delete()

        # The branch connection commits, then the default connection's commit fails.
        # Armed once the sync body's last step ran, so the failing commit is the one that closes it.
        default = connections[DEFAULT_DB_ALIAS]
        real_commit = default.commit
        real_advance = Branch._advance_sync_baselines
        armed, failed = [], []

        def advance_and_arm(branch_self, *args, **kwargs):
            real_advance(branch_self, *args, **kwargs)
            armed.append(True)

        def commit_once_failing():
            if armed and not failed:
                failed.append(True)
                raise DatabaseError('simulated failure of the default commit')
            return real_commit()

        with (
            patch.object(Branch, '_advance_sync_baselines', advance_and_arm),
            patch.object(default, 'commit', commit_once_failing),
            self.assertRaises(DatabaseError),
        ):
            branch.sync(user=self.user)
        self.assertTrue(failed)
        synced = self._branch_state(branch)
        self.assertIn('Created', [name for _, name, _ in synced[0]], 'the branch commit landed')

        # The next sync must neither fail replaying those changes nor alter the branch.
        branch.refresh_from_db()
        self.assertEqual(branch.status, BranchStatusChoices.READY)
        branch.sync(user=self.user)
        branch.refresh_from_db()
        self.assertEqual(branch.status, BranchStatusChoices.READY)
        self.assertEqual(self._branch_state(branch), synced)

    def test_sync_right_after_provisioning_does_not_replay_its_snapshot(self):
        """
        A sync run within the watermark margin of provisioning used to move the watermark before the
        provisioning time; the next sync replayed the changes the branch had been created with.
        """
        with event_tracking(self.request):
            Site.objects.create(name='Before', slug='before')
        branch = provision_branch(user=self.user)
        with event_tracking(self.request):
            Site.objects.create(name='After 1', slug='after-1')
        branch.sync(user=self.user)
        with event_tracking(self.request):
            Site.objects.create(name='After 2', slug='after-2')
        branch.refresh_from_db()
        branch.sync(user=self.user)
        branch.refresh_from_db()
        self.assertEqual(branch.status, BranchStatusChoices.READY)
        self.assertEqual([name for _, name, _ in self._branch_state(branch)[0]], ['Before', 'After 1', 'After 2'])

    def test_main_change_during_sync_reaches_change_diff(self):
        with event_tracking(self.request):
            site = Site.objects.create(name='Site', slug='site')
        branch = provision_branch(user=self.user)
        with activate_branch(branch), event_tracking(self.request):
            in_branch = Site.objects.get(pk=site.pk)
            in_branch.snapshot()
            in_branch.description = 'changed in branch'
            in_branch.save()
        diff = ChangeDiff.objects.get(branch=branch, object_id=site.pk)
        self.assertFalse(diff.conflicts)

        # main changes the same object while the branch is syncing (or migrating, or pending migrations)
        for status in (
            BranchStatusChoices.READY,
            BranchStatusChoices.SYNCING,
            BranchStatusChoices.MIGRATING,
            BranchStatusChoices.PENDING_MIGRATIONS,
        ):
            Branch.objects.filter(pk=branch.pk).update(status=status)
            with event_tracking(self.request):
                site.snapshot()
                site.description = f'changed in main while {status}'
                site.save()
            diff.refresh_from_db()
            self.assertEqual(diff.current['description'], f'changed in main while {status}', status)
            self.assertIn('description', diff.conflicts or [], status)
