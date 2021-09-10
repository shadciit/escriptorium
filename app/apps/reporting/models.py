from datetime import datetime, timezone

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from core.models import Document, DocumentPart
from django.db.models import Count, Sum, F
import re

User = get_user_model()


class TaskReport(models.Model):
    WORKFLOW_STATE_QUEUED = 0
    WORKFLOW_STATE_STARTED = 1
    WORKFLOW_STATE_ERROR = 2
    WORKFLOW_STATE_DONE = 3
    WORKFLOW_STATE_CHOICES = (
        (WORKFLOW_STATE_QUEUED, _("Queued")),
        (WORKFLOW_STATE_STARTED, _("Running")),
        (WORKFLOW_STATE_ERROR, _("Crashed")),
        (WORKFLOW_STATE_DONE, _("Finished"))
    )

    workflow_state = models.PositiveSmallIntegerField(
        default=WORKFLOW_STATE_QUEUED,
        choices=WORKFLOW_STATE_CHOICES
    )
    label = models.CharField(max_length=256)
    messages = models.TextField(blank=True)

    queued_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True)
    done_at = models.DateTimeField(null=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # celery task id
    task_id = models.CharField(max_length=64, blank=True, null=True)

    # shared_task method name
    method = models.CharField(max_length=512, blank=True, null=True)

    cpu_cost = models.FloatField(blank=True, null=True)
    gpu_cost = models.FloatField(blank=True, null=True)

    def append(self, text):
        self.messages += text + '\n'

    @property
    def uri(self):
        return reverse('report-detail', kwargs={'pk': self.pk})

    def start(self, task_id, method):
        self.task_id = task_id
        self.method = method
        self.workflow_state = self.WORKFLOW_STATE_STARTED
        self.started_at = datetime.now(timezone.utc)
        self.save()

    def error(self, message):
        # unrecoverable error
        self.workflow_state = self.WORKFLOW_STATE_ERROR
        self.done_at = datetime.now(timezone.utc)
        self.append(message)
        self.save()

    def end(self, extra_links=None):
        self.workflow_state = self.WORKFLOW_STATE_DONE
        self.done_at = datetime.now(timezone.utc)
        self.save()

    def calc_cpu_cost(self, nb_cores):
        task_duration = (self.done_at - self.started_at).total_seconds()
        self.cpu_cost = (task_duration * nb_cores * settings.CPU_COST_FACTOR) / 60
        self.save()

    def calc_gpu_cost(self):
        task_duration = (self.done_at - self.started_at).total_seconds()
        self.gpu_cost = (task_duration * settings.GPU_COST) / 60
        self.save()


class ProjectReport:
    def __init__(self, project):
        project_document = (Document
                            .objects
                            .filter(project=project)
                            .annotate(_part_count=Count('parts'))
                            .annotate(_part_lines_count=Count('parts__lines'))
                            .annotate(_part_lines_transcriptions=F('parts__lines__transcriptions__content'))
                            .annotate(_part_lines_block=Count('parts__lines__block', distinct=True))
                            .values('shared_with_groups', 'shared_with_users', '_part_count', '_part_lines_count', '_part_lines_transcriptions', '_part_lines_block'))
        self.project_documentpart_total = self.aggregate_value(project_document, '_part_count')
        self.project_documentpart_rows_total = self.aggregate_value(project_document, '_part_lines_count')
        self.project_documentpart_region_total = self.aggregate_value(project_document, '_part_lines_block')
        self.project_create_at = project.created_at
        self.project_update_at = project.updated_at
        self.project_shared_group_total = project.shared_with_groups.all().count()
        self.project_shared_users_total = project.shared_with_users.all().count()
        self.project_document_group_shared_total = project_document.filter(shared_with_groups__isnull=False).count()
        self.project_document_user_shared_total = project_document.filter(shared_with_users__isnull=False).count()
        self.all_transcription_content = re.sub(r'[^\w\s]','', ' '.join([i for i in project_document.values_list('_part_lines_transcriptions', flat=True) if i]))
        self.project_documentpart_rows_words_total = len(self.all_transcription_content.split())
        self.project_documentpart_rows_characters_total = len(self.all_transcription_content.strip().replace(" ", ""))
        self.project_documentpart_vocabulary = ' '.join(sorted(set(self.simplify_text(self.all_transcription_content))))
    
    def aggregate_value(self, model, field):
        return model.aggregate(Sum(field)).get(field + '__sum')
    
    def simplify_text(self, text):
        import unicodedata
        try:
            text = unicode(text, 'utf-8')
        except NameError:
            pass
        text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode("utf-8")
        return str(text).strip().replace(" ", "")

