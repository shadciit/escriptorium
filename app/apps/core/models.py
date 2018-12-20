from django.db import models
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.postgres.fields import ArrayField, JSONField
from django.utils.translation import gettext as _
from django.core.files.storage import FileSystemStorage
from django.core.validators import FileExtensionValidator

import click
import celery
from celery import chain
from ordered_model.models import OrderedModel
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFit

from versioning.models import Versioned
from .tasks import generate_part_thumbnails, segment, binarize, transcribe

User = get_user_model()


class Typology(models.Model):
    """
    Document: map, poem, novel ..
    Part: page, log, cover ..
    Block: main text, floating text, illustration, 
    """
    TARGET_DOCUMENT = 1
    TARGET_PART = 2
    TARGET_BLOCK = 3
    TARGET_CHOICES = (
        (TARGET_DOCUMENT, 'Document'),
        (TARGET_PART, 'Part (eg Page)'),
        (TARGET_BLOCK, 'Block (eg Paragraph)'),
    )
    name = models.CharField(max_length=128)
    target = models.PositiveSmallIntegerField(choices=TARGET_CHOICES)
    
    def __str__(self):
        return self.name


class Metadata(models.Model):
    name = models.CharField(max_length=128, unique=True)
    cidoc_id = models.CharField(max_length=8, null=True, blank=True)

    class Meta:
        ordering = ('name',)
    
    def __str__(self):
        return self.name


class DocumentMetadata(models.Model):
    document = models.ForeignKey('core.Document', on_delete=models.CASCADE)
    key = models.ForeignKey(Metadata, on_delete=models.CASCADE)
    value = models.CharField(max_length=512)
    
    def __str__(self):
        return '%s:%s' % (self.document.name, self.key.name)
    

class DocumentManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related('typology')
    
    def for_user(self, user):
        # return the list of editable documents
        # Note: Monitor this query
        return (Document.objects
                .filter(Q(owner=user)
                        | (Q(workflow_state__gt=Document.WORKFLOW_STATE_DRAFT)
                          & (Q(shared_with_users=user)
                             | Q(shared_with_groups__in=user.groups.all())
                          ))
                )
                .exclude(workflow_state=Document.WORKFLOW_STATE_ARCHIVED)
                .prefetch_related('shared_with_groups')
                .select_related('typology')
                .distinct()
        )


class Document(models.Model):
    WORKFLOW_STATE_DRAFT = 0
    WORKFLOW_STATE_SHARED = 1  # editable a viewable by shared_with people
    WORKFLOW_STATE_PUBLISHED = 2  # viewable by the world
    WORKFLOW_STATE_ARCHIVED = 3  # 
    WORKFLOW_STATE_CHOICES = (
        (WORKFLOW_STATE_DRAFT, _("Draft")),
        (WORKFLOW_STATE_SHARED, _("Shared")),
        (WORKFLOW_STATE_PUBLISHED, _("Published")),
        (WORKFLOW_STATE_ARCHIVED, _("Archived")),
    )
    
    name = models.CharField(max_length=512)
    
    owner = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    workflow_state = models.PositiveSmallIntegerField(
        default=WORKFLOW_STATE_DRAFT,
        choices=WORKFLOW_STATE_CHOICES)
    shared_with_users = models.ManyToManyField(User, blank=True,
                                               verbose_name=_("Share with users"),
                                               related_name='shared_documents')
    shared_with_groups = models.ManyToManyField(Group, blank=True,
                                                verbose_name=_("Share with teams"),
                                                related_name='shared_documents')
    
    typology = models.ForeignKey(Typology, null=True, blank=True, on_delete=models.SET_NULL,
                                 limit_choices_to={'target': Typology.TARGET_DOCUMENT})
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    metadatas = models.ManyToManyField(Metadata, through=DocumentMetadata, blank=True)
    
    objects = DocumentManager()
    
    class Meta:
        ordering = ('-updated_at',)
    
    def __str__(self):
        return self.name
    
    @property
    def is_shared(self):
        return self.workflow_state in [self.WORKFLOW_STATE_PUBLISHED,
                                       self.WORKFLOW_STATE_SHARED]    
    @property
    def is_published(self):
        return self.workflow_state == self.WORKFLOW_STATE_PUBLISHED
    
    @property
    def is_archived(self):
        return self.workflow_state == self.WORKFLOW_STATE_ARCHIVED

    
def document_images_path(instance, filename):
    return 'documents/%d/%s' % (instance.document.pk, filename)


class DocumentPart(OrderedModel):
    """
    Represents a physical part of a larger document that is usually a page
    """
    name = models.CharField(max_length=512, blank=True)
    image_source = models.ImageField(upload_to=document_images_path)
    image = ImageSpecField(source='image_source', id='core:large')
    bw_backend = models.CharField(max_length=128, default='kraken')
    bw_image = models.ImageField(upload_to=document_images_path, null=True, blank=True)
    typology = models.ForeignKey(Typology, null=True, blank=True,
                                 on_delete=models.SET_NULL,
                                 limit_choices_to={'target': Typology.TARGET_PART})
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='parts')
    order_with_respect_to = 'document'
    
    WORKFLOW_STATE_CREATED = 0
    WORKFLOW_STATE_BINARIZING = 1
    WORKFLOW_STATE_BINARIZED = 2
    WORKFLOW_STATE_SEGMENTING = 3
    WORKFLOW_STATE_SEGMENTED = 4
    WORKFLOW_STATE_TRANSCRIBING = 5
    WORKFLOW_STATE_CHOICES = (
        (WORKFLOW_STATE_CREATED, _("Created")),
        (WORKFLOW_STATE_BINARIZING, _("Binarizing")),
        (WORKFLOW_STATE_BINARIZED, _("Binarized")),
        (WORKFLOW_STATE_SEGMENTING, _("Segmenting")),
        (WORKFLOW_STATE_SEGMENTED, _("Segmented")),
        (WORKFLOW_STATE_TRANSCRIBING, _("Transcribing")),
    )
    workflow_state = models.PositiveSmallIntegerField(choices=WORKFLOW_STATE_CHOICES,
                                                      default=WORKFLOW_STATE_CREATED)
    
    # this is denormalization because, it's too 
    transcription_progress = models.PositiveSmallIntegerField(default=0)
    
    class Meta(OrderedModel.Meta):
        pass
    
    def __str__(self):
        if self.name:
            return self.name
        return '%s %d' % (self.typology or _("Element"), self.order + 1)

    @property
    def title(self):
        return str(self)
    
    @property
    def binarized(self):
        return self.workflow_state >= self.WORKFLOW_STATE_BINARIZED
    
    @property
    def segmented(self):
        return self.workflow_state >= self.WORKFLOW_STATE_SEGMENTED
    
    def calculate_progress(self):
        transcribed = LineTranscription.objects.filter(line__document_part=self).count()
        total = Line.objects.filter(document_part=self).count()
        if not total:
            return 0
        return int(transcribed / total * 100)

    def save(self, *args, **kwargs):
        if not self.pk:
            # generate the thumbnails asynchronously
            # because we don't want to generate 200 at once
            generate_part_thumbnails.delay(self.pk)
        self.calculate_progress()
        return super().save(*args, **kwargs)
    
    def binarize(self, user_pk=None):
        binarize.delay(self.pk, user_pk=user_pk)
    
    def segment(self, user_pk=None):
        if not self.binarized:
            chain(binarize.si(self.pk, user_pk=user_pk),
                  segment.si(self.pk, user_pk=user_pk)).delay()
        else:
            segment.delay(self.pk, user_pk=user_pk)
    
    def transcribe(self, user_pk=None):
        if not self.segmented:
            chain(binarize.si(self.pk, user_pk=user_pk),
                  segment.si(self.pk, user_pk=user_pk),
                  transcribe.si(self.pk, user_pk=user_pk)).delay()
        else:
            transcribe.delay(self.pk, user_pk=user_pk)


class Block(models.Model):
    """
    Represents a visualy close group of graphemes (characters) bound by the same semantic 
    example: a paragraph, a margin note or floating text
    A Block is not directly bound to a DocumentPart to avoid a useless join or denormalization
    when fetching the content of a DocumentPart.
    """
    typology = models.ForeignKey(Typology, null=True, on_delete=models.SET_NULL,
                                 limit_choices_to={'target': Typology.TARGET_BLOCK})
    document_part = models.ForeignKey(DocumentPart, on_delete=models.CASCADE)
    
    def box(self):
        # TODO
        return None


class Line(OrderedModel):  # Versioned, 
    """
    Represents a segmented line from a DocumentPart
    """
    # box = models.BoxField()  # in case we use PostGIS
    box = JSONField()
    document_part = models.ForeignKey(DocumentPart, on_delete=models.CASCADE, related_name='lines')
    block = models.ForeignKey(Block, null=True, on_delete=models.SET_NULL)
    script = models.CharField(max_length=8, null=True, blank=True)  # choices ??
    # text direction
    order_with_respect_to = 'document_part'
    version_ignore_fields = ('document_part', 'order')
    
    class Meta(OrderedModel.Meta):
        pass

    def __str__(self):
        return '%s#%d' % (self.document_part, self.order)
    
    # def save(self, *args, **kwargs):
    #     # validate char_boxes
    #     return super().save(*args, **kwargs)


class Transcription(models.Model):
    name = models.CharField(max_length=512)
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (('name', 'document'),)


class LineTranscription(Versioned, models.Model):
    """
    Represents a transcribded line of a document part in a given transcription
    """
    transcription = models.ForeignKey(Transcription, on_delete=models.CASCADE)
    text = models.CharField(null=True, max_length=2048)
    # graphs = [  # WIP
    # {c: <graph_code>, bbox: ((x1, y1), (x2, y2)), confidence: 0-1}
    # ]
    graphs = JSONField(null=True, blank=True)  # on postgres it maps to jsonb!
    
    # nullable in case we re-segment ?? for now we lose data.
    line = models.OneToOneField(Line, null=True, on_delete=models.SET_NULL)
    version_ignore_fields = ('line', 'transcription')


kraken_storage = FileSystemStorage(location=click.get_app_dir('kraken'))

class OcrModel(models.Model):
    name = models.CharField(max_length=256, unique=True)
    file = models.FileField(storage=kraken_storage,
                            validators=[FileExtensionValidator(
                                allowed_extensions=['clstm', 'pronn'])])
    trained = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name


class DocumentProcessSettings(models.Model):
    document = models.OneToOneField(Document, on_delete=models.CASCADE,
                                    related_name='process_settings')
    auto_process = models.BooleanField(default=True)
    text_direction = models.CharField(max_length=64, default='horizontal-lr',
                                      choices=(('horizontal-lr', _("Horizontal")),
                                               ('vertical-lr', _("Vertical"))))
    binarizer = models.CharField(max_length=64,
                                 choices=(('kraken', _("Kraken")),),
                                 default='kraken')
    ocrmodel = models.ForeignKey(OcrModel, verbose_name=_("Model"),
                                 null=True, blank=True, on_delete=models.SET_NULL,
                                 limit_choices_to={'trained': True})
    typology = models.ForeignKey(Typology,
                                 null=True, blank=True, on_delete=models.SET_NULL,
                                 limit_choices_to={'target': Typology.TARGET_PART})

    def __str__(self):
        return 'Processing settings for %s' % self.document
