"""
Branch status transitions are compare-and-set (F1, F14).

Two jobs used to both pass an in-memory "ready" check and run the same operation on a branch, and a
failing job's rollback could overwrite the status another job had set (a merged branch back to ready).
"""

from unittest.mock import patch

from django.db.models.signals import post_save
from django.test import TestCase

from core.models import ObjectChange
from netbox_branching.choices import BranchStatusChoices
from netbox_branching.models import Branch
from netbox_branching.signals import post_merge


class StatusTransitionTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        branch = Branch(name='Branch 1')
        branch.status = BranchStatusChoices.READY  # Fake provisioning
        branch.save(provision=False)

    def setUp(self):
        self.branch = Branch.objects.get(name='Branch 1')

    def _status(self):
        return Branch.objects.get(pk=self.branch.pk).status

    def test_transition_is_compare_and_set(self):
        self.assertTrue(self.branch._transition_status(BranchStatusChoices.READY, BranchStatusChoices.MERGING))
        # The branch is no longer READY: a second transition from READY does nothing.
        self.assertFalse(self.branch._transition_status(BranchStatusChoices.READY, BranchStatusChoices.SYNCING))
        self.assertEqual(self._status(), BranchStatusChoices.MERGING)

    def test_second_merge_aborts_without_touching_the_branch(self):
        """
        A merge whose in-memory branch still reads READY, while another job already set MERGING, must not
        run (it used to replay the change log a second time).
        """
        stale = Branch.objects.get(pk=self.branch.pk)  # loaded while READY
        Branch.objects.filter(pk=self.branch.pk).update(status=BranchStatusChoices.MERGING)  # the other job
        with patch.object(Branch, '_merge_locked') as body, self.assertRaisesMessage(Exception, 'not ready to merge'):
            stale.merge(user=None)
        body.assert_not_called()
        self.assertEqual(self._status(), BranchStatusChoices.MERGING)

    def test_second_sync_aborts_without_touching_the_branch(self):
        stale = Branch.objects.get(pk=self.branch.pk)
        Branch.objects.filter(pk=self.branch.pk).update(status=BranchStatusChoices.SYNCING)
        with (
            patch.object(Branch, 'is_stale', False),
            patch.object(Branch, '_sync_locked') as body,
            self.assertRaisesMessage(Exception, 'not ready to sync'),
        ):
            stale.sync(user=None)
        body.assert_not_called()
        self.assertEqual(self._status(), BranchStatusChoices.SYNCING)

    def test_failed_merge_does_not_reopen_a_branch_another_job_merged(self):
        """
        A rollback only restores READY if the status is still the transitional one this job set: a merged
        branch must not go back to READY because a concurrent merge failed (it then accepted writes again).
        """

        def merged_elsewhere_then_fail(branch, user, commit, logger):
            Branch.objects.filter(pk=branch.pk).update(status=BranchStatusChoices.MERGED)  # the other job
            branch._transition_status(BranchStatusChoices.MERGING, BranchStatusChoices.READY)  # the rollback
            raise RuntimeError('duplicate key')

        with patch.object(Branch, '_merge_locked', merged_elsewhere_then_fail), self.assertRaises(RuntimeError):
            self.branch.merge(user=None)
        self.assertEqual(self._status(), BranchStatusChoices.MERGED)

    def test_merge_does_not_finish_if_its_status_was_changed(self):
        """The final MERGING -> MERGED is a compare-and-set too."""
        Branch.objects.filter(pk=self.branch.pk).update(status=BranchStatusChoices.READY)
        self.branch.status = BranchStatusChoices.MERGING
        Branch.objects.filter(pk=self.branch.pk).update(status=BranchStatusChoices.READY)  # someone reset it
        self.assertFalse(self.branch._transition_status(BranchStatusChoices.MERGING, BranchStatusChoices.MERGED))
        self.assertEqual(self._status(), BranchStatusChoices.READY)

    def test_exception_in_post_merge_disconnects_the_applied_change_recorder(self):
        """A failing post_merge receiver used to leave record_applied_change connected in the worker (F14)."""
        receivers_before = len(post_save._live_receivers(ObjectChange)[0])

        def boom(**kwargs):
            raise RuntimeError('post_merge receiver failed')

        post_merge.connect(boom, weak=False)
        self.addCleanup(post_merge.disconnect, boom)
        with (
            patch.object(Branch, 'get_unmerged_changes') as changes,
            patch('netbox_branching.models.branches.get_merge_strategy'),
            self.assertRaisesMessage(RuntimeError, 'post_merge receiver failed'),
        ):
            changes.return_value.order_by.return_value = [object()]
            self.branch.merge(user=None)
        self.assertEqual(len(post_save._live_receivers(ObjectChange)[0]), receivers_before)
        self.assertEqual(self._status(), BranchStatusChoices.MERGED)
