"""
A change written to a branch while it is being merged, or after it was merged, must never be lost (F2).

The branch write lock keeps HTTP write requests out of a merge, but writes made outside a request (a
script or job using activate_branch()) do not take it. The merge therefore checks, before committing,
that every change in the branch was part of it, and archive() refuses to drop a schema holding changes
recorded after the merge.
"""

import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connections
from django.test import RequestFactory
from django.urls import reverse

from dcim.models import Site
from netbox.context_managers import event_tracking
from netbox_branching.choices import BranchMergeStrategyChoices, BranchStatusChoices
from netbox_branching.merge_strategies.iterative import IterativeMergeStrategy
from netbox_branching.merge_strategies.squash import SquashMergeStrategy
from netbox_branching.models import Branch
from netbox_branching.tests.utils import FastTeardownTransactionTestCase, provision_branch
from netbox_branching.utilities import BranchHasUnmergedChanges, activate_branch

User = get_user_model()


class MergeVerificationTestCase(FastTeardownTransactionTestCase):
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

    def _write_in_branch(self, branch, name):
        with activate_branch(branch), event_tracking(self.request):
            Site.objects.create(name=name, slug=name.lower())

    def _merge_with_late_write(self, strategy):
        """Merge a branch while a write outside any request lands in it during the merge."""
        branch = provision_branch(user=self.user, name=f'Branch {strategy}', merge_strategy=strategy)
        self._write_in_branch(branch, 'Early')
        strategy_class = IterativeMergeStrategy if strategy == BranchMergeStrategyChoices.ITERATIVE else SquashMergeStrategy
        original = strategy_class.merge

        def merge_then_write(strategy_self, *args, **kwargs):
            original(strategy_self, *args, **kwargs)
            self._write_in_branch(branch, 'Late')  # committed on the branch connection, unseen by the merge

        with patch.object(strategy_class, 'merge', merge_then_write), self.assertRaisesMessage(
            Exception, 'written to branch'
        ):
            branch.merge(user=self.user)

        branch.refresh_from_db()
        self.assertEqual(branch.status, BranchStatusChoices.READY)
        self.assertFalse(Site.objects.filter(name='Early').exists(), 'the failed merge must roll back')

        # Merging again applies both changes.
        branch.merge(user=self.user)
        branch.refresh_from_db()
        self.assertEqual(branch.status, BranchStatusChoices.MERGED)
        self.assertEqual(set(Site.objects.values_list('name', flat=True)), {'Early', 'Late'})

    def test_late_write_fails_iterative_merge(self):
        self._merge_with_late_write(BranchMergeStrategyChoices.ITERATIVE)

    def test_late_write_fails_squash_merge(self):
        self._merge_with_late_write(BranchMergeStrategyChoices.SQUASH)

    def test_archive_refuses_branch_with_changes_after_merge(self):
        branch = provision_branch(user=self.user)
        self._write_in_branch(branch, 'Merged')
        branch.merge(user=self.user)
        branch.refresh_from_db()

        # A write that bypassed the status check after the merge (e.g. a script using activate_branch())
        self._write_in_branch(branch, 'After')

        with self.assertRaisesMessage(BranchHasUnmergedChanges, 'made after it was merged'):
            branch.archive(user=self.user)
        branch.refresh_from_db()
        self.assertEqual(branch.status, BranchStatusChoices.MERGED)
        with activate_branch(branch):
            self.assertTrue(Site.objects.filter(name='After').exists(), 'the schema must not have been dropped')

    def test_archive_merged_branch(self):
        branch = provision_branch(user=self.user)
        self._write_in_branch(branch, 'Merged')
        branch.merge(user=self.user)
        branch.refresh_from_db()

        branch.archive(user=self.user)
        branch.refresh_from_db()
        self.assertEqual(branch.status, BranchStatusChoices.ARCHIVED)
