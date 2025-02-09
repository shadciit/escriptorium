"""
The goal here is not to test drf internals
but only our own layer on top of it.
So no need to test the content unless there is some magic in the serializer.
"""

import unittest
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from core.models import (
    Block,
    Document,
    DocumentMetadata,
    Line,
    LineTranscription,
    LineType,
    Metadata,
    OcrModel,
    Transcription,
)
from core.tests.factory import CoreFactoryTestCase
from reporting.models import TaskGroup


class UserViewSetTestCase(CoreFactoryTestCase):

    def setUp(self):
        super().setUp()
        self.user = self.factory.make_user()
        self.user2 = self.factory.make_user()
        self.admin = self.factory.make_user(is_staff=True)

    def test_simple_list(self):
        self.client.force_login(self.user)
        uri = reverse('api:user-list')
        with self.assertNumQueries(6):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)

    def test_simple_detail(self):
        self.client.force_login(self.user)
        uri = reverse('api:user-detail', kwargs={'pk': self.user.pk})
        with self.assertNumQueries(5):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)

    def test_only_admins_see_everyone(self):
        self.client.force_login(self.user)
        uri = reverse('api:user-list')
        resp = self.client.get(uri)
        self.assertEqual(resp.data['count'], 1)

        self.client.force_login(self.admin)
        resp = self.client.get(uri)
        self.assertEqual(resp.data['count'], 3)

    def test_user_cant_access_another_user(self):
        self.client.force_login(self.user)
        uri = reverse('api:user-detail', kwargs={'pk': self.user2.pk})
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 404)

    def test_get_project_tags(self):
        project = self.factory.make_project()
        tag = self.factory.make_project_tag(user=self.user)
        project.tags.add(tag)
        self.client.force_login(self.user)
        uri = reverse('api:project-tag-list')
        with self.assertNumQueries(4):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_create_project_tag(self):
        self.client.force_login(self.user)

        uri = reverse('api:project-tag-list')
        with self.assertNumQueries(3):
            resp = self.client.post(uri, {
                'name': 'test-tag',
                'color': '#123456'
            })
            self.assertEqual(resp.status_code, 201, resp.content)

    def test_get_current_user(self):
        uri = reverse('api:user-current')

        # should respond with 401 unauthorized if not logged in
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 401)

        # should respond with the current user with status 200 when logged in
        self.client.force_login(self.user)
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["pk"], self.user.pk)
        self.assertEqual(resp.json()["is_staff"], False)

        # should correctly respond for an admin user is_staff=True
        self.client.force_login(self.admin)
        resp = self.client.get(uri)
        self.assertEqual(resp.json()["pk"], self.admin.pk)
        self.assertEqual(resp.json()["is_staff"], True)


class DocumentViewSetTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.proj1 = self.factory.make_project(name='proj1')
        self.proj2 = self.factory.make_project(name='proj2', owner=self.proj1.owner)
        self.doc = self.factory.make_document(project=self.proj1, owner=self.proj1.owner)
        self.doc2 = self.factory.make_document(project=self.proj2, owner=self.proj1.owner)
        self.part = self.factory.make_part(document=self.doc)
        self.part2 = self.factory.make_part(document=self.doc)

        self.line = Line.objects.create(
            baseline=[[10, 25], [50, 25]],
            mask=[[10, 10], [50, 10], [50, 50], [10, 50]],
            document_part=self.part)
        self.line2 = Line.objects.create(
            baseline=[[10, 80], [50, 80]],
            mask=[[10, 60], [50, 60], [50, 100], [10, 100]],
            document_part=self.part)
        self.transcription = Transcription.objects.create(
            document=self.part.document,
            name='test')
        self.transcription2 = Transcription.objects.create(
            document=self.part.document,
            name='tr2')
        self.lt = LineTranscription.objects.create(
            transcription=self.transcription,
            line=self.line,
            content='test')
        self.lt2 = LineTranscription.objects.create(
            transcription=self.transcription2,
            line=self.line2,
            content='test2')

    def test_list(self):
        self.client.force_login(self.doc.owner)
        uri = reverse('api:document-list')
        with self.assertNumQueries(20):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)

    def test_detail(self):
        self.client.force_login(self.doc.owner)
        uri = reverse('api:document-detail',
                      kwargs={'pk': self.doc.pk})
        with self.assertNumQueries(12):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)

    def test_perm(self):
        user = self.factory.make_user()
        self.client.force_login(user)
        uri = reverse('api:document-detail',
                      kwargs={'pk': self.doc.pk})
        resp = self.client.get(uri)
        # Note: raises a 404 instead of 403 but its fine
        self.assertEqual(resp.status_code, 404)

    def test_segtrain_less_two_parts(self):
        self.client.force_login(self.doc.owner)
        model = self.factory.make_model(self.doc, job=OcrModel.MODEL_JOB_SEGMENT)
        uri = reverse('api:document-segtrain', kwargs={'pk': self.doc.pk})
        resp = self.client.post(uri, data={
            'parts': [self.part.pk],
            'model': model.pk
        })

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], {'parts': [
            'Segmentation training requires at least 2 images.']})

    def test_share_group(self):
        self.client.force_login(self.doc.owner)
        group = self.factory.make_group(users=[self.doc.owner])

        uri = reverse('api:document-share', kwargs={'pk': self.doc.pk})
        resp = self.client.post(uri, {'group': group.pk})

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['shared_with_groups'][0]['pk'], group.pk)

    def test_share_group_not_part_of(self):
        self.client.force_login(self.doc.owner)
        group = self.factory.make_group()  # owner is not part of the group

        uri = reverse('api:document-share', kwargs={'pk': self.doc.pk})
        resp = self.client.post(uri, {'group': group.pk})

        self.assertEqual(resp.status_code, 400)

    def test_share_user(self):
        self.client.force_login(self.doc.owner)
        user = self.factory.make_user()

        uri = reverse('api:document-share', kwargs={'pk': self.doc.pk})
        resp = self.client.post(uri, {'user': user.username})

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['shared_with_users'][0]['pk'], user.pk)

    @unittest.skip
    def test_segtrain_new_model(self):
        # This test breaks CI as it consumes too many resources
        self.client.force_login(self.doc.owner)
        uri = reverse('api:document-segtrain', kwargs={'pk': self.doc.pk})
        resp = self.client.post(uri, data={
            'parts': [self.part.pk, self.part2.pk],
            'model_name': 'new model'
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(OcrModel.objects.count(), 1)
        self.assertEqual(OcrModel.objects.first().name, "new model")

    @unittest.expectedFailure
    def test_segtrain_existing_model_rename(self):
        self.client.force_login(self.doc.owner)
        model = self.factory.make_model(self.doc, job=OcrModel.MODEL_JOB_SEGMENT)
        uri = reverse('api:document-segtrain', kwargs={'pk': self.doc.pk})
        resp = self.client.post(uri, data={
            'parts': [self.part.pk, self.part2.pk],
            'model': model.pk,
            'model_name': 'test new model'
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(OcrModel.objects.count(), 2)

    @unittest.expectedFailure
    def test_segment(self):
        uri = reverse('api:document-segment', kwargs={'pk': self.doc.pk})
        self.client.force_login(self.doc.owner)
        model = self.factory.make_model(self.doc, job=OcrModel.MODEL_JOB_SEGMENT)
        resp = self.client.post(uri, data={
            'parts': [self.part.pk, self.part2.pk],
            'seg_steps': 'both',
            'model': model.pk,
        })
        self.assertEqual(resp.status_code, 200)

    @unittest.skip
    def test_train_new_model(self):
        self.client.force_login(self.doc.owner)
        uri = reverse('api:document-train', kwargs={'pk': self.doc.pk})
        resp = self.client.post(uri, data={
            'parts': [self.part.pk, self.part2.pk],
            'model_name': 'testing new model',
            'transcription': self.transcription.pk
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.doc.ocr_models.filter(job=OcrModel.MODEL_JOB_RECOGNIZE).count(), 1)

    @unittest.expectedFailure
    def test_transcribe(self):
        trans = Transcription.objects.create(document=self.part.document)

        self.client.force_login(self.doc.owner)
        model = self.factory.make_model(self.doc, job=OcrModel.MODEL_JOB_RECOGNIZE)
        uri = reverse('api:document-transcribe', kwargs={'pk': self.doc.pk})
        resp = self.client.post(uri, data={
            'parts': [self.part.pk, self.part2.pk],
            'model': model.pk,
            'transcription': trans.pk
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, b'{"status":"ok"}')
        # won't work with dummy model and image
        # self.assertEqual(LineTranscription.objects.filter(transcription=trans).count(), 2)

    def test_align(self):
        self.client.force_login(self.doc.owner)
        uri = reverse('api:document-align', kwargs={'pk': self.doc.pk})

        witness = self.factory.make_witness(owner=self.doc.owner)

        resp = self.client.post(uri, data={
            'parts': [self.part.pk, self.part2.pk],
            'transcription': Transcription.objects.first().pk,

            "existing_witness": witness.pk,
            "n_gram": 2,
            "max_offset": 20,
            "merge": False,
            "full_doc": True,
            "threshold": 0.8,
            "region_types": ["Orphan", "Undefined"],
            "layer_name": "example",
            # "beam_size": 10,
            "gap": 1000000,
        })

        self.assertEqual(resp.status_code, 200, resp.content)

    def test_list_document_with_tasks(self):
        # Creating a new Document that self.doc.owner shouldn't see
        other_doc = self.factory.make_document(project=self.factory.make_project(name="Test API"))
        report1 = other_doc.reports.create(user=other_doc.owner, label="Fake report")
        report1.start()
        report2 = self.doc.reports.create(user=self.doc.owner, label="Fake report")
        report2.start()

        self.client.force_login(self.doc.owner)
        with self.assertNumQueries(6):
            resp = self.client.get(reverse('api:document-tasks'))

        json = resp.json()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json['count'], 1)
        self.assertEqual(json['results'], [{
            'pk': self.doc.pk,
            'name': self.doc.name,
            'owner': self.doc.owner.username,
            'tasks_stats': {'Queued': 0, 'Running': 1, 'Crashed': 0, 'Finished': 0, 'Canceled': 0},
            'last_started_task': self.doc.reports.latest('started_at').started_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }])

    def test_list_document_with_tasks_staff_user(self):
        self.doc.owner.is_staff = True
        self.doc.owner.save()
        # Creating a new Document that self.doc.owner should also see since he is a staff member
        other_doc = self.factory.make_document(project=self.factory.make_project(name="Test API"))
        report = other_doc.reports.create(user=other_doc.owner, label="Fake report")
        report.start()
        report2 = self.doc.reports.create(user=self.doc.owner, label="Fake report")
        report2.start()

        self.client.force_login(self.doc.owner)
        with self.assertNumQueries(8):
            resp = self.client.get(reverse('api:document-tasks'))

        self.assertEqual(resp.status_code, 200)
        json = resp.json()
        self.assertEqual(json['count'], 2)
        self.assertEqual(json['results'], [
            {
                'pk': other_doc.pk,
                'name': other_doc.name,
                'owner': other_doc.owner.username,
                'tasks_stats': {'Queued': 0, 'Running': 1, 'Crashed': 0, 'Finished': 0, 'Canceled': 0},
                'last_started_task': other_doc.reports.latest('started_at').started_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            },
            {
                'pk': self.doc.pk,
                'name': self.doc.name,
                'owner': self.doc.owner.username,
                'tasks_stats': {'Queued': 0, 'Running': 1, 'Crashed': 0, 'Finished': 0, 'Canceled': 0},
                'last_started_task': self.doc.reports.latest('started_at').started_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            },
        ])

    def test_list_document_with_tasks_filter_wrong_user_id(self):
        self.doc.owner.is_staff = True
        self.doc.owner.save()
        self.client.force_login(self.doc.owner)
        resp = self.client.get(reverse('api:document-tasks') + '?user_id=blablabla')

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json(), {'error': 'Invalid user_id, it should be an int.'})

    def test_list_document_with_tasks_filter_user_id_disabled_for_normal_user(self):
        # Creating a new Document that self.doc.owner shouldn't see
        other_doc = self.factory.make_document(project=self.factory.make_project(name="Test API"))
        report = other_doc.reports.create(user=other_doc.owner, label="Fake report")
        report.start()
        report2 = self.doc.reports.create(user=self.doc.owner, label="Fake report")
        report2.start()

        self.client.force_login(self.doc.owner)
        with self.assertNumQueries(6):
            # Filtering by user_id but the user is not part of the staff so the filter will be ignored
            resp = self.client.get(reverse('api:document-tasks') + f"?user_id={other_doc.owner.id}")

        self.assertEqual(resp.status_code, 200)
        json = resp.json()
        self.assertEqual(json['count'], 1)
        self.assertEqual(json['results'], [{
            'pk': self.doc.pk,
            'name': self.doc.name,
            'owner': self.doc.owner.username,
            'tasks_stats': {'Queued': 0, 'Running': 1, 'Crashed': 0, 'Finished': 0, 'Canceled': 0},
            'last_started_task': self.doc.reports.latest('started_at').started_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }])

    def test_list_document_with_tasks_filter_user_id(self):
        self.doc.owner.is_staff = True
        self.doc.owner.save()
        other_doc = self.factory.make_document(project=self.factory.make_project(name="Test API"))
        report = other_doc.reports.create(user=other_doc.owner, label="Fake report")
        report.start()

        self.client.force_login(self.doc.owner)
        with self.assertNumQueries(6):
            resp = self.client.get(reverse('api:document-tasks') + f"?user_id={other_doc.owner.id}")

        self.assertEqual(resp.status_code, 200)
        json = resp.json()
        self.assertEqual(json['count'], 1)
        self.assertEqual(json['results'], [
            {
                'pk': other_doc.pk,
                'name': other_doc.name,
                'owner': other_doc.owner.username,
                'tasks_stats': {'Queued': 0, 'Running': 1, 'Crashed': 0, 'Finished': 0, 'Canceled': 0},
                'last_started_task': other_doc.reports.latest('started_at').started_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            }
        ])

    def test_list_document_with_tasks_filter_name(self):
        self.doc.owner.is_staff = True
        self.doc.owner.save()
        other_doc = self.factory.make_document(name="other doc", project=self.factory.make_project(name="Test API"))
        report = other_doc.reports.create(user=other_doc.owner, label="Fake report")
        report.start()

        self.client.force_login(self.doc.owner)
        with self.assertNumQueries(6):
            resp = self.client.get(reverse('api:document-tasks') + "?name=other")

        self.assertEqual(resp.status_code, 200)
        json = resp.json()
        self.assertEqual(json['count'], 1)
        self.assertEqual(json['results'], [
            {
                'pk': other_doc.pk,
                'name': other_doc.name,
                'owner': other_doc.owner.username,
                'tasks_stats': {'Queued': 0, 'Running': 1, 'Crashed': 0, 'Finished': 0, 'Canceled': 0},
                'last_started_task': other_doc.reports.latest('started_at').started_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            }
        ])

    def test_list_document_with_tasks_filter_wrong_task_state(self):
        self.client.force_login(self.doc.owner)
        resp = self.client.get(reverse('api:document-tasks') + '?task_state=wrongstate')

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json(), {'error': 'Invalid task_state, it should match a valid workflow_state.'})

    def test_list_document_with_tasks_filter_task_state(self):
        self.doc.owner.is_staff = True
        self.doc.owner.save()
        other_doc = self.factory.make_document(project=self.factory.make_project(name="Test API"))
        report = other_doc.reports.create(user=other_doc.owner, label="Fake report")
        report.start()

        self.client.force_login(self.doc.owner)
        with self.assertNumQueries(6):
            resp = self.client.get(reverse('api:document-tasks') + "?task_state=Running")

        self.assertEqual(resp.status_code, 200)
        json = resp.json()
        self.assertEqual(json['count'], 1)
        self.assertEqual(json['results'], [
            {
                'pk': other_doc.pk,
                'name': other_doc.name,
                'owner': other_doc.owner.username,
                'tasks_stats': {'Queued': 0, 'Running': 1, 'Crashed': 0, 'Finished': 0, 'Canceled': 0},
                'last_started_task': other_doc.reports.latest('started_at').started_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            },
        ])

    def test_cancel_all_tasks_for_document_not_found(self):
        self.client.force_login(self.doc.owner)
        with self.assertNumQueries(3):
            resp = self.client.post(reverse('api:document-cancel-tasks', kwargs={'pk': 2000}))
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json(), {
            'error': "Document with pk 2000 doesn't exist",
            'status': 'Not Found'
        })

    def test_cancel_all_tasks_for_document_forbidden(self):
        # A normal user can't stop all tasks on a document he don't own
        user = self.factory.make_user()
        self.client.force_login(user)
        with self.assertNumQueries(4):
            resp = self.client.post(reverse('api:document-cancel-tasks', kwargs={'pk': self.doc.pk}))
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json(), {
            'detail': 'You do not have permission to perform this action.'
        })

    @patch('escriptorium.celery.app.control.revoke')
    def test_cancel_all_tasks_for_document(self, mock_revoke):
        self.client.force_login(self.doc.owner)

        # Simulating a pending task
        report = self.doc.reports.create(user=self.doc.owner, label="Fake report", task_id="11111", method="core.tasks.train")

        # Simulating a running training task
        report2 = self.doc.reports.create(user=self.doc.owner, label="Fake report", task_id="22222", method="core.tasks.train")
        report2.start()
        model = self.factory.make_model(self.doc, job=OcrModel.MODEL_JOB_SEGMENT)
        model.training = True
        model.save()

        # Asserting that there is a running task on self.doc
        resp = self.client.get(reverse('api:document-tasks'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['results'], [{
            'pk': self.doc.pk,
            'name': self.doc.name,
            'owner': self.doc.owner.username,
            'tasks_stats': {'Queued': 1, 'Running': 1, 'Crashed': 0, 'Finished': 0, 'Canceled': 0},
            'last_started_task': self.doc.reports.filter(started_at__isnull=False).latest('started_at').started_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }])

        # Stopping all tasks on self.doc
        def fake_revoke(id, terminate=False):
            if id == "11111":
                report.error('Canceled by celery')
            else:
                report2.error('Canceled by celery')

        mock_revoke.side_effect = fake_revoke
        with self.assertNumQueries(16):
            resp = self.client.post(reverse('api:document-cancel-tasks', kwargs={'pk': self.doc.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {
            'status': 'canceled',
            'details': f'Canceled 2 pending/running tasks linked to document {self.doc.name}.'
        })
        self.assertEqual(mock_revoke.call_count, 2)

        # Assert that there is no more tasks running on self.doc
        resp = self.client.get(reverse('api:document-tasks'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['results'], [{
            'pk': self.doc.pk,
            'name': self.doc.name,
            'owner': self.doc.owner.username,
            'tasks_stats': {'Queued': 0, 'Running': 0, 'Crashed': 0, 'Finished': 0, 'Canceled': 2},
            'last_started_task': self.doc.reports.filter(started_at__isnull=False).latest('started_at').started_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }])
        model.refresh_from_db()
        self.assertEqual(model.training, False)

    @patch('escriptorium.celery.app.control.revoke')
    def test_cancel_all_tasks_for_document_staff_user(self, mock_revoke):
        # This user doesn't own self.doc but can cancel all of its tasks since he is a staff member
        user = self.factory.make_user()
        user.is_staff = True
        user.save()
        self.client.force_login(user)

        # Simulating a pending task
        report = self.doc.reports.create(user=self.doc.owner, label="Fake report", task_id="11111", method="core.tasks.train")

        # Simulating a running training task
        report2 = self.doc.reports.create(user=self.doc.owner, label="Fake report", task_id="22222", method="core.tasks.train")
        report2.start()
        model = self.factory.make_model(self.doc, job=OcrModel.MODEL_JOB_SEGMENT)
        model.training = True
        model.save()

        # Asserting that there is a running task on self.doc
        resp = self.client.get(reverse('api:document-tasks'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['results'], [{
            'pk': self.doc.pk,
            'name': self.doc.name,
            'owner': self.doc.owner.username,
            'tasks_stats': {'Queued': 1, 'Running': 1, 'Crashed': 0, 'Finished': 0, 'Canceled': 0},
            'last_started_task': self.doc.reports.filter(started_at__isnull=False).latest('started_at').started_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }])

        # Stopping all tasks on self.doc
        def fake_revoke(id, terminate=False):
            if id == "11111":
                report.error('Canceled by celery')
            else:
                report2.error('Canceled by celery')

        mock_revoke.side_effect = fake_revoke
        with self.assertNumQueries(15):
            resp = self.client.post(reverse('api:document-cancel-tasks', kwargs={'pk': self.doc.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {
            'status': 'canceled',
            'details': f'Canceled 2 pending/running tasks linked to document {self.doc.name}.'
        })
        self.assertEqual(mock_revoke.call_count, 2)

        # Assert that there is no more tasks running on self.doc
        resp = self.client.get(reverse('api:document-tasks'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['results'], [{
            'pk': self.doc.pk,
            'name': self.doc.name,
            'owner': self.doc.owner.username,
            'tasks_stats': {'Queued': 0, 'Running': 0, 'Crashed': 0, 'Finished': 0, 'Canceled': 2},
            'last_started_task': self.doc.reports.filter(started_at__isnull=False).latest('started_at').started_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }])
        model.refresh_from_db()
        self.assertEqual(model.training, False)

    def test_task_group(self):
        # make fake reports
        group = TaskGroup.objects.create(created_by=self.doc.owner, document=self.doc)

        # pending
        self.doc.reports.create(user=self.doc.owner, label="Fake report", group=group,
                                task_id="11111", method="core.tasks.train")
        # running
        report2 = self.doc.reports.create(user=self.doc.owner, label="Fake report", group=group,
                                          task_id="22222", method="core.tasks.train")
        report2.start()
        # canceled
        report3 = self.doc.reports.create(user=self.doc.owner, label="Fake report", group=group,
                                          task_id="33333", method="core.tasks.train")
        report3.cancel(self.doc.owner)
        # error
        report4 = self.doc.reports.create(user=self.doc.owner, label="Fake report", group=group,
                                          task_id="44444", method="core.tasks.train")
        report4.error("Something terrible happened.")
        # finished
        report5 = self.doc.reports.create(user=self.doc.owner, label="Fake report", group=group,
                                          task_id="55555", method="core.tasks.train")
        report5.end()
        report6 = self.doc.reports.create(user=self.doc.owner, label="Fake report", group=group,
                                          task_id="66666", method="core.tasks.train")
        report6.end()

        self.client.force_login(self.doc.owner)
        uri = reverse('api:task-group-list', kwargs={'document_pk': self.doc.pk})
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['results'][0]['method'], "core.tasks.train")
        data = {t['workflow_state']: t['count'] for t in resp.json()['results'][0]['tasks']}
        self.assertEqual(data['Queued'], 1)
        self.assertEqual(data['Running'], 1)
        self.assertEqual(data['Crashed'], 1)
        self.assertEqual(data['Finished'], 2)
        self.assertEqual(data['Canceled'], 1)

    def test_unrelated_task_group(self):
        group = TaskGroup.objects.create(created_by=self.doc.owner, document=self.doc)
        # unrelated group
        group2 = TaskGroup.objects.create(created_by=self.doc.owner, document=self.doc2)

        report = self.doc.reports.create(user=self.doc.owner, label="Fake report", group=group,
                                         task_id="111111", method="core.tasks.train")
        report.end()
        report2 = self.doc.reports.create(user=self.doc.owner, label="Fake report", group=group2,
                                          task_id="222222", method="core.tasks.train")
        report2.end()

        self.client.force_login(self.doc.owner)
        uri = reverse('api:task-group-list', kwargs={'document_pk': self.doc.pk})
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['count'], 1)
        data = {t['workflow_state']: t['count'] for t in resp.json()['results'][0]['tasks']}
        self.assertEqual(data['Finished'], 1)

    def test_filter_project(self):
        self.client.force_login(self.doc.owner)
        uri = reverse('api:document-list')
        resp = self.client.get(uri)
        self.assertEqual(resp.json()['count'], 2)

        resp = self.client.get(uri + '?project=' + str(self.doc.project.pk))
        self.assertEqual(resp.json()['count'], 1)
        self.assertEqual(resp.json()['results'][0]['pk'], self.doc.pk)

    def test_filter_tags(self):
        tag1 = self.factory.make_document_tag(project=self.doc.project, name='tag1')
        tag2 = self.factory.make_document_tag(project=self.doc.project, name='tag2')
        self.doc.tags.add(tag1)
        self.doc2.tags.add(tag1)
        self.doc2.tags.add(tag2)

        self.client.force_login(self.doc.owner)
        uri = reverse('api:document-list')
        resp = self.client.get(uri)
        self.assertEqual(resp.json()['count'], 2)

        resp = self.client.get(uri + '?tags=' + str(tag1.pk))
        self.assertEqual(resp.json()['count'], 2)

        resp = self.client.get(uri + '?tags=' + str(tag2.pk))
        self.assertEqual(resp.json()['count'], 1)
        self.assertEqual(resp.json()['results'][0]['pk'], self.doc2.pk)

        # test OR logic
        resp = self.client.get(uri + '?tags=' + str(tag1.pk) + '|' + str(tag2.pk))
        self.assertEqual(resp.json()['count'], 2)

        # test AND logic
        resp = self.client.get(uri + '?tags=' + str(tag1.pk) + ',' + str(tag2.pk))
        self.assertEqual(resp.json()['count'], 1)

    def test_filter_no_tag(self):
        tag1 = self.factory.make_document_tag(project=self.doc.project)
        self.doc.tags.add(tag1)

        self.client.force_login(self.doc.owner)
        uri = reverse('api:document-list')
        resp = self.client.get(uri)
        self.assertEqual(resp.json()['count'], 2)

        resp = self.client.get(uri + '?tags=none')
        self.assertEqual(resp.json()['count'], 1)
        self.assertEqual(resp.json()['results'][0]['pk'], self.doc2.pk)

        resp = self.client.get(uri + '?tags=none|' + str(tag1.pk))
        self.assertEqual(resp.json()['count'], 2)

    def test_stats(self):
        part = self.factory.make_part(document=self.doc)
        transcription = self.factory.make_transcription(document=self.doc)
        self.factory.make_content(part, transcription=transcription)
        self.factory.make_img_annotations(part)
        self.factory.make_text_annotations(part, transcription)

        self.client.force_login(self.doc.owner)
        uri = reverse('api:document-stats', kwargs={'pk': self.doc.pk})
        with self.assertNumQueries(9):
            resp = self.client.get(uri)
            self.assertEqual(resp.status_code, 200)

            self.assertEqual(resp.data["regions"][0]["typology_name"], "blocktype")
            self.assertEqual(resp.data["regions"][0]["frequency"], 1)
            self.assertEqual(resp.data["lines"][0]["typology_name"], "linetype0")
            self.assertEqual(resp.data["lines"][0]["frequency"], 6)
            self.assertEqual(resp.data["lines"][1]["typology_name"], "linetype1")
            self.assertEqual(resp.data["lines"][1]["frequency"], 6)

            self.assertEqual(resp.data["image_annotations"][0]["taxonomy_name"], "imgtaxo")
            self.assertEqual(resp.data["image_annotations"][0]["frequency"], 3)

            self.assertEqual(resp.data["text_annotations"][0]["taxonomy_name"], "texttaxo")
            self.assertEqual(resp.data["text_annotations"][0]["frequency"], 3)


class PartViewSetTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.part = self.factory.make_part()
        self.part2 = self.factory.make_part(document=self.part.document)  # scaling test
        self.user = self.part.document.owner  # shortcut

    @override_settings(THUMBNAIL_ENABLE=False)
    def test_list(self):
        self.client.force_login(self.user)
        uri = reverse('api:part-list',
                      kwargs={'document_pk': self.part.document.pk})
        with self.assertNumQueries(9):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)

    def test_list_perm(self):
        user = self.factory.make_user()
        self.client.force_login(user)
        uri = reverse('api:part-list',
                      kwargs={'document_pk': self.part.document.pk})
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 403)

    @override_settings(THUMBNAIL_ENABLE=False)
    def test_detail(self):
        self.client.force_login(self.user)
        uri = reverse('api:part-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'pk': self.part.pk})
        with self.assertNumQueries(11):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)

    def test_detail_perm(self):
        user = self.factory.make_user()
        self.client.force_login(user)
        uri = reverse('api:part-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'pk': self.part.pk})
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 403)

    @override_settings(THUMBNAIL_ENABLE=False)
    def test_create(self):
        self.client.force_login(self.user)
        uri = reverse('api:part-list',
                      kwargs={'document_pk': self.part.document.pk})
        with self.assertNumQueries(22):
            img = self.factory.make_image_file()
            resp = self.client.post(uri, {
                'image': SimpleUploadedFile(
                    'test.png', img.read())})
        self.assertEqual(resp.status_code, 201)

    @override_settings(THUMBNAIL_ENABLE=False)
    def test_update(self):
        self.client.force_login(self.user)
        uri = reverse('api:part-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'pk': self.part.pk})
        with self.assertNumQueries(8):
            resp = self.client.patch(
                uri, {'transcription_progress': 50},
                content_type='application/json')
            self.assertEqual(resp.status_code, 200, resp.content)

    def test_move(self):
        self.client.force_login(self.user)
        uri = reverse('api:part-move',
                      kwargs={'document_pk': self.part2.document.pk,
                              'pk': self.part2.pk})
        with self.assertNumQueries(6):
            resp = self.client.post(uri, {'index': 0})
            self.assertEqual(resp.status_code, 200)

        self.part2.refresh_from_db()
        self.assertEqual(self.part2.order, 0)


class DocumentMetadataTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.doc = self.factory.make_document()
        metadatakey1 = Metadata.objects.create(name='testmeta1')
        self.dm1 = DocumentMetadata.objects.create(document=self.doc, key=metadatakey1, value='testval1')
        metadatakey2 = Metadata.objects.create(name='testmeta2')
        self.dm2 = DocumentMetadata.objects.create(document=self.doc, key=metadatakey2, value='testval2')

    def test_detail(self):
        self.client.force_login(self.doc.owner)
        uri = reverse('api:metadata-detail',
                      kwargs={'document_pk': self.doc.pk,
                              'pk': self.dm1.pk})
        with self.assertNumQueries(6):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["key"], {"name": "testmeta1", "cidoc_id": None})
        self.assertEqual(resp.json()["value"], "testval1")

    def test_list(self):
        self.client.force_login(self.doc.owner)
        uri = reverse('api:metadata-list',
                      kwargs={'document_pk': self.doc.pk})
        with self.assertNumQueries(8):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['count'], 2)

    def test_create(self):
        self.client.force_login(self.doc.owner)
        uri = reverse('api:metadata-list',
                      kwargs={'document_pk': self.doc.pk})
        with self.assertNumQueries(8):
            resp = self.client.post(uri, {
                'key': {'name': 'testnewkey'},
                'value': 'testnewval'
            }, content_type='application/json')
        self.assertEqual(resp.status_code, 201, resp.content)


class BlockViewSetTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.part = self.factory.make_part()
        self.user = self.part.document.owner
        for i in range(2):
            b = Block.objects.create(
                box=[10 + 50 * i, 10, 50 + 50 * i, 50],
                document_part=self.part)
        self.block = b

    def test_detail(self):
        self.client.force_login(self.user)
        uri = reverse('api:block-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk,
                              'pk': self.block.pk})
        with self.assertNumQueries(4):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)

    def test_list(self):
        self.client.force_login(self.user)
        uri = reverse('api:block-list',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk})
        with self.assertNumQueries(5):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)

    def test_create(self):
        self.client.force_login(self.user)
        uri = reverse('api:block-list',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk})
        with self.assertNumQueries(5):
            # 1-2: auth
            # 3 select document_part
            # 4 select max block order
            # 5 insert
            resp = self.client.post(uri, {
                'document_part': self.part.pk,
                'box': '[[10,10], [20,20], [50,50]]'
            })
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_update(self):
        self.client.force_login(self.user)
        uri = reverse('api:block-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk,
                              'pk': self.block.pk})
        with self.assertNumQueries(5):
            resp = self.client.patch(uri, {
                'box': '[[100,100], [150,150]]'
            }, content_type='application/json')
        self.assertEqual(resp.status_code, 200, resp.content)


class LineViewSetTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.part = self.factory.make_part()
        self.user = self.part.document.owner
        self.block = Block.objects.create(
            box=[[10, 10], [10, 200], [200, 200], [200, 10]],
            document_part=self.part)
        self.line_type = LineType.objects.create(name='linetype')
        self.line = Line.objects.create(
            baseline=[[0, 0], [10, 10], [20, 20]],
            document_part=self.part,
            block=self.block,
            typology=self.line_type)
        self.line2 = Line.objects.create(
            document_part=self.part,
            block=self.block)
        self.orphan = Line.objects.create(
            baseline=[[30, 30], [40, 40], [50, 50]],
            document_part=self.part,
            block=None)

    # not used
    # def test_detail(self):
    # def test_list(self):

    def test_create(self):
        self.client.force_login(self.user)
        uri = reverse('api:line-list',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk})
        with self.assertNumQueries(5):
            resp = self.client.post(uri, {
                'document_part': self.part.pk,
                'baseline': '[[10, 10], [50, 50]]'
            })
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(self.part.lines.count(), 4)  # 3 + 1 new

    def test_update(self):
        self.client.force_login(self.user)
        uri = reverse('api:line-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk,
                              'pk': self.line.pk})
        with self.assertNumQueries(5):
            resp = self.client.patch(uri, {
                'baseline': '[[100,100], [150,150]]'
            }, content_type='application/json')
            self.assertEqual(resp.status_code, 200)
        self.line.refresh_from_db()
        self.assertEqual(self.line.baseline, '[[100,100], [150,150]]')

    def test_bulk_delete(self):
        self.client.force_login(self.user)
        uri = reverse('api:line-bulk-delete',
                      kwargs={'document_pk': self.part.document.pk, 'part_pk': self.part.pk})
        with self.assertNumQueries(12):
            resp = self.client.post(uri, {'lines': [self.line.pk]},
                                    content_type='application/json')
        self.assertEqual(Line.objects.count(), 2)
        self.assertEqual(resp.status_code, 200)

    def test_bulk_update(self):
        self.client.force_login(self.user)
        uri = reverse('api:line-bulk-update',
                      kwargs={'document_pk': self.part.document.pk, 'part_pk': self.part.pk})
        with self.assertNumQueries(7):
            resp = self.client.put(uri, {'lines': [
                {'pk': self.line.pk,
                 'mask': '[[60, 40], [60, 50], [90, 50], [90, 40]]',
                 'region': None},
                {'pk': self.line2.pk,
                 'mask': '[[50, 40], [50, 30], [70, 30], [70, 40]]',
                 'region': self.block.pk}
            ]}, content_type='application/json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.line.refresh_from_db()
        self.line2.refresh_from_db()
        self.assertEqual(self.line.mask, '[[60, 40], [60, 50], [90, 50], [90, 40]]')
        self.assertEqual(self.line2.mask, '[[50, 40], [50, 30], [70, 30], [70, 40]]')

    def test_bulk_update_order(self):
        order1, order2 = self.line.order, self.line2.order
        self.client.force_login(self.user)

        uri = reverse('api:line-bulk-update',
                      kwargs={'document_pk': self.part.document.pk, 'part_pk': self.part.pk})
        resp = self.client.put(uri, {'lines': [
            {'pk': self.line.pk, 'order': order2},
            {'pk': self.line2.pk, 'order': order1}
        ]}, content_type='application/json')
        self.assertEqual(resp.status_code, 200, resp.content)

        self.line.refresh_from_db()
        self.line2.refresh_from_db()
        self.assertEqual(self.line.order, order2)
        self.assertEqual(self.line2.order, order1)

    def test_merge(self):
        self.client.force_login(self.user)
        uri = reverse('api:line-merge',
                      kwargs={'document_pk': self.part.document.pk, 'part_pk': self.part.pk})

        # First merge will fail, because line2 doesn't have a baseline
        body = {'lines': [self.line.pk, self.line2.pk, self.orphan.pk]}
        resp = self.client.post(uri, body, content_type="application/json")
        self.assertEqual(resp.status_code, 400, resp.content)

        # second merge will fail, because 'lines' is mandatory
        body = {}
        resp = self.client.post(uri, body, content_type="application/json")
        self.assertEqual(resp.status_code, 400, resp.content)

        # third merge should succeed
        body = {'lines': [self.line.pk, self.orphan.pk]}
        resp = self.client.post(uri, body, content_type="application/json")
        self.assertEqual(resp.status_code, 200, resp.content)

        created_pk = resp.data['lines']['created']['pk']
        created = Line.objects.get(pk=created_pk)
        self.assertEqual(created.typology.pk, self.line_type.pk)
        self.assertEqual(created.block.pk, self.block.pk)
        self.assertEqual(created.baseline, self.line.baseline + self.orphan.baseline)

        self.assertIsNone(Line.objects.filter(pk=self.line.pk).first())
        self.assertIsNone(Line.objects.filter(pk=self.orphan.pk).first())
        self.assertIsNotNone(Line.objects.filter(pk=self.line2.pk).first())


class TranscriptionViewSetTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.part = self.factory.make_part()
        self.user = self.part.document.owner
        self.transcription = self.factory.make_transcription(document=self.part.document)

    def test_stats(self):
        self.factory.make_content(self.part, transcription=self.transcription)
        self.client.force_login(self.user)
        uri = reverse('api:transcription-stats', kwargs={
            'document_pk': self.part.document.pk,
            'pk': self.transcription.pk
        })

        with self.assertNumQueries(6):
            resp = self.client.get(uri)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.data['characters'][0]['char'], ' ')
            self.assertEqual(resp.data['characters'][0]['frequency'], 191)
            self.assertEqual(resp.data['characters'][1]['char'], 'e')
            self.assertEqual(resp.data['characters'][1]['frequency'], 44)
            self.assertEqual(resp.data['characters'][2]['char'], 'M')
            self.assertEqual(resp.data['characters'][2]['frequency'], 43)
            self.assertEqual(resp.data['characters'][-1]['char'], 'I')
            self.assertEqual(resp.data['characters'][-1]['frequency'], 20)

            self.assertEqual(resp.data['line_count'], 30)

    def test_stats_ordering(self):
        self.factory.make_content(self.part, transcription=self.transcription)
        self.client.force_login(self.user)
        uri = reverse('api:transcription-stats', kwargs={
            'document_pk': self.part.document.pk,
            'pk': self.transcription.pk
        }) + '?ordering=char'
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['characters'][0]['char'], ' ')
        self.assertEqual(resp.data['characters'][-1]['char'], 'Z')


class LineTranscriptionViewSetTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.part = self.factory.make_part()
        self.user = self.part.document.owner
        self.line = Line.objects.create(
            mask=[10, 10, 50, 50],
            document_part=self.part)
        self.line2 = Line.objects.create(
            mask=[10, 60, 50, 100],
            document_part=self.part)
        self.transcription = Transcription.objects.create(
            document=self.part.document,
            name='test')
        self.transcription2 = Transcription.objects.create(
            document=self.part.document,
            name='tr2')
        self.lt = LineTranscription.objects.create(
            transcription=self.transcription,
            line=self.line,
            content='test')
        self.lt2 = LineTranscription.objects.create(
            transcription=self.transcription2,
            line=self.line2,
            content='test2')

    def test_update(self):
        self.client.force_login(self.user)
        uri = reverse('api:linetranscription-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk,
                              'pk': self.lt.pk})
        with self.assertNumQueries(5):
            resp = self.client.patch(uri, {
                'content': 'update'
            }, content_type='application/json')
        self.assertEqual(resp.status_code, 200)

    def test_create(self):
        self.client.force_login(self.user)
        uri = reverse('api:linetranscription-list',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk})

        with self.assertNumQueries(12):
            resp = self.client.post(uri, {
                'line': self.line2.pk,
                'transcription': self.transcription.pk,
                'content': 'new'
            }, content_type='application/json')
        self.assertEqual(resp.status_code, 201)

    def test_new_version(self):
        self.client.force_login(self.user)
        uri = reverse('api:linetranscription-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk,
                              'pk': self.lt.pk})

        with self.assertNumQueries(7):
            resp = self.client.put(uri, {'content': 'test',
                                         'transcription': self.lt.transcription.pk,
                                         'line': self.lt.line.pk},
                                   content_type='application/json')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.lt.refresh_from_db()
        self.assertEqual(len(self.lt.versions), 1)

    def test_bulk_create(self):
        self.client.force_login(self.user)
        uri = reverse('api:linetranscription-bulk-create',
                      kwargs={'document_pk': self.part.document.pk, 'part_pk': self.part.pk})
        ll = Line.objects.create(
            mask=[10, 10, 50, 50],
            document_part=self.part)
        with self.assertNumQueries(10):
            resp = self.client.post(
                uri,
                {'lines': [
                    {'line': ll.pk,
                     'transcription': self.transcription.pk,
                     'content': 'new transcription'},
                    {'line': ll.pk,
                     'transcription': self.transcription2.pk,
                     'content': 'new transcription 2'},
                ]}, content_type='application/json')
            self.assertEqual(resp.status_code, 200)

    def test_bulk_update(self):
        self.client.force_login(self.user)
        uri = reverse('api:linetranscription-bulk-update',
                      kwargs={'document_pk': self.part.document.pk, 'part_pk': self.part.pk})

        with self.assertNumQueries(18):
            resp = self.client.put(uri, {'lines': [
                {'pk': self.lt.pk,
                 'content': 'test1 new',
                 'transcription': self.transcription.pk,
                 'line': self.line.pk},
                {'pk': self.lt2.pk,
                 'content': 'test2 new',
                 'transcription': self.transcription.pk,
                 'line': self.line2.pk},
            ]}, content_type='application/json')
            self.lt.refresh_from_db()
            self.lt2.refresh_from_db()
            self.assertEqual(self.lt.content, "test1 new")
            self.assertEqual(self.lt2.content, "test2 new")
            self.assertEqual(self.lt2.transcription, self.transcription)
            self.assertEqual(resp.status_code, 200)

    def test_bulk_delete(self):
        self.client.force_login(self.user)
        uri = reverse('api:linetranscription-bulk-delete',
                      kwargs={'document_pk': self.part.document.pk, 'part_pk': self.part.pk})
        with self.assertNumQueries(5):
            resp = self.client.post(uri, {'lines': [self.lt.pk, self.lt2.pk]},
                                    content_type='application/json')
            lines = LineTranscription.objects.all()
            self.assertEqual(lines[0].content, "")
            self.assertEqual(lines[1].content, "")
            self.assertEqual(resp.status_code, 204)


class OcrModelViewSetTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.factory.make_user()

    def test_list(self):
        self.client.force_login(self.user)
        uri = reverse('api:ocrmodel-list')
        with self.assertNumQueries(3):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)

    def test_create(self):
        self.client.force_login(self.user)
        uri = reverse('api:ocrmodel-list')
        model = SimpleUploadedFile("test_model.mlmodel",
                                   b"file_content")
        resp = self.client.post(uri, {'name': 'test_model',
                                      'job': 'Segment',
                                      'file': model})
        self.assertEqual(resp.status_code, 201)

    def test_shared_user(self):
        doc = self.factory.make_document()
        user2 = self.factory.make_user()
        model = self.factory.make_model(doc)
        model.ocr_model_rights.create(ocr_model=model, user=user2)

        self.client.force_login(user2)
        uri = reverse('api:ocrmodel-list')
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200, resp.json())
        self.assertEqual(resp.json()['count'], 1)

    def test_shared_group(self):
        doc = self.factory.make_document()
        user2 = self.factory.make_user()
        group = self.factory.make_group(users=[user2])
        model = self.factory.make_model(doc)
        model.ocr_model_rights.create(ocr_model=model, group=group)

        self.client.force_login(user2)
        uri = reverse('api:ocrmodel-list')
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200, resp.json())
        self.assertEqual(resp.json()['count'], 1)

    def test_no_duplicates(self):
        # regression test
        doc = self.factory.make_document(owner=self.user)
        user2 = self.factory.make_user()
        model = self.factory.make_model(doc)
        group = self.factory.make_group(users=[self.user, user2])
        model.ocr_model_rights.create(ocr_model=model, user=user2)
        model.ocr_model_rights.create(ocr_model=model, group=group)

        self.client.force_login(self.user)
        uri = reverse('api:ocrmodel-list')
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200, resp.json())
        self.assertEqual(resp.json()['count'], 1, resp.json())


class ProjectViewSetTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.project = self.factory.make_project()

    def test_regression_read_all_projects(self):
        other_user = self.factory.make_user()
        self.factory.make_project(owner=other_user)
        self.client.force_login(self.project.owner)
        uri = reverse('api:project-list')
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['count'], 1)

    def test_create(self):
        self.client.force_login(self.project.owner)
        uri = reverse('api:project-list')
        resp = self.client.post(uri, {'name': 'test proj'})
        self.assertEqual(resp.status_code, 201)

    def test_documents_count(self):
        self.factory.make_document(project=self.project)
        uri = reverse('api:project-list')
        self.client.force_login(self.project.owner)
        resp = self.client.get(uri)
        self.assertEqual(resp.json()['results'][0]['documents_count'], 1)
        # adding an archived document should not increase the count
        self.factory.make_document(project=self.project, workflow_state=Document.WORKFLOW_STATE_ARCHIVED)
        resp = self.client.get(uri)
        self.assertEqual(resp.json()['results'][0]['documents_count'], 1)

    def test_add_tag_to_project(self):
        tag = self.factory.make_project_tag(user=self.project.owner)
        self.client.force_login(self.project.owner)
        uri = reverse('api:project-detail', kwargs={'pk': self.project.pk})
        with self.assertNumQueries(13):
            resp = self.client.patch(uri, {
                'tags': [tag.pk]
            }, content_type='application/json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(self.project.tags.count(), 1)

    def test_remove_tag_from_project(self):
        tag1 = self.factory.make_project_tag(name='tag1', user=self.project.owner)
        tag2 = self.factory.make_project_tag(name='tag2', user=self.project.owner)
        self.project.tags.add(tag1)
        self.project.tags.add(tag2)
        self.assertEqual(self.project.tags.count(), 2)
        self.client.force_login(self.project.owner)
        uri = reverse('api:project-detail', kwargs={'pk': self.project.pk})
        with self.assertNumQueries(13):
            resp = self.client.patch(uri, {
                'tags': [tag2.pk]
            }, content_type='application/json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(self.project.tags.count(), 1)

    def test_filter_tags(self):
        project2 = self.factory.make_project(owner=self.project.owner, name='proj2')
        self.factory.make_project(owner=self.project.owner, name='proj3')
        tag1 = self.factory.make_project_tag(user=self.project.owner, name='tag1')
        tag2 = self.factory.make_project_tag(user=self.project.owner, name='tag2')
        self.project.tags.add(tag1)
        project2.tags.add(tag1)
        project2.tags.add(tag2)

        self.client.force_login(self.project.owner)
        uri = reverse('api:project-list')
        resp = self.client.get(uri)
        self.assertEqual(resp.json()['count'], 3)

        resp = self.client.get(uri + '?tags=' + str(tag1.pk))
        self.assertEqual(resp.json()['count'], 2)

        resp = self.client.get(uri + '?tags=' + str(tag2.pk))
        self.assertEqual(resp.json()['count'], 1)
        self.assertEqual(resp.json()['results'][0]['id'], project2.pk)

        # test OR logic
        resp = self.client.get(uri + '?tags=' + str(tag1.pk) + '|' + str(tag2.pk))
        self.assertEqual(resp.json()['count'], 2)

        # test AND logic
        resp = self.client.get(uri + '?tags=' + str(tag1.pk) + ',' + str(tag2.pk))
        self.assertEqual(resp.json()['count'], 1)

    def test_filter_no_tag(self):
        tag1 = self.factory.make_project_tag(user=self.project.owner)
        self.project.tags.add(tag1)
        project_without_tag = self.factory.make_project(name="proj without tags",
                                                        owner=self.project.owner)

        self.client.force_login(self.project.owner)
        uri = reverse('api:project-list')
        resp = self.client.get(uri)

        self.assertEqual(resp.json()['count'], 2)

        resp = self.client.get(uri + '?tags=none')
        self.assertEqual(resp.json()['count'], 1)
        self.assertEqual(resp.json()['results'][0]['id'], project_without_tag.pk)

        resp = self.client.get(uri + '?tags=none|' + str(tag1.pk))
        self.assertEqual(resp.json()['count'], 2)

    def test_share_group(self):
        self.client.force_login(self.project.owner)
        group = self.factory.make_group(users=[self.project.owner])

        uri = reverse('api:project-share', kwargs={'pk': self.project.pk})
        resp = self.client.post(uri, {'group': group.pk})

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['shared_with_groups'][0]['pk'], group.pk)

    def test_share_group_not_part_of(self):
        self.client.force_login(self.project.owner)
        group = self.factory.make_group()  # owner is not part of the group

        uri = reverse('api:project-share', kwargs={'pk': self.project.pk})
        resp = self.client.post(uri, {'group': group.pk})

        self.assertEqual(resp.status_code, 400)

    def test_share_user(self):
        self.client.force_login(self.project.owner)
        user = self.factory.make_user()

        uri = reverse('api:project-share', kwargs={'pk': self.project.pk})
        resp = self.client.post(uri, {'user': user.username})

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['shared_with_users'][0]['pk'], user.pk)


class DocumentPartMetadataTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.part = self.factory.make_part()
        self.user = self.part.document.owner

    def test_create(self):
        self.client.force_login(self.user)
        uri = reverse('api:partmetadata-list',
                      kwargs={'document_pk': self.part.document.pk, 'part_pk': self.part.pk})
        with self.assertNumQueries(8):
            resp = self.client.post(uri, {'key': {'name': 'testname', 'cidoc': 'testcidoc'},
                                          'value': 'testvalue'},
                                    content_type='application/json')
        mds = self.part.metadata.all()
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(mds[0].key.name, "testname")
        self.assertEqual(mds[0].value, "testvalue")

    def test_create_existing_key(self):
        self.client.force_login(self.user)
        self.factory.make_part_metadata(self.part)
        uri = reverse('api:partmetadata-list',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk})
        with self.assertNumQueries(5):
            resp = self.client.post(uri, {'key': {'name': 'testmd'},
                                          'value': 'testvalue2'},
                                    content_type='application/json')
        mds = self.part.metadata.all().order_by('id')
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(mds[0].key.name, "testmd")
        self.assertEqual(mds[0].value, "testmdvalue")
        self.assertEqual(mds[1].key.name, "testmd")
        self.assertEqual(mds[1].value, "testvalue2")

    def test_update_key(self):
        md = self.factory.make_part_metadata(self.part)
        self.client.force_login(self.user)
        uri = reverse('api:partmetadata-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk,
                              'pk': md.pk})
        with self.assertNumQueries(8):
            resp = self.client.patch(uri, {'key': {'name': 'testname2'}},
                                     content_type='application/json')
        self.assertEqual(resp.status_code, 200, resp.content)
        mds = self.part.metadata.all()
        self.assertEqual(mds[0].key.name, "testname2")

    def test_update_value(self):
        self.client.force_login(self.user)
        md = self.factory.make_part_metadata(self.part)
        uri = reverse('api:partmetadata-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk,
                              'pk': md.pk})
        with self.assertNumQueries(7):
            resp = self.client.patch(uri, {'value': 'testvalue2'},
                                     content_type='application/json')
        self.assertEqual(resp.status_code, 200, resp.content)
        mds = self.part.metadata.all()
        self.assertEqual(mds[0].value, "testvalue2")

    def test_delete(self):
        self.client.force_login(self.user)
        md = self.factory.make_part_metadata(self.part)
        uri = reverse('api:partmetadata-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk,
                              'pk': md.pk})
        with self.assertNumQueries(5):
            resp = self.client.delete(uri)
        self.assertEqual(resp.status_code, 204, resp.content)
        self.assertEqual(self.part.metadata.count(), 0)
