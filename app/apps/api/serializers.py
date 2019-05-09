import bleach
import logging
import json

from django.conf import settings
from rest_framework import serializers
from easy_thumbnails.files import get_thumbnailer


from core.models import *

logger = logging.getLogger(__name__)


class ImageField(serializers.ImageField):
    def __init__(self, *args, thumbnails=None, **kwargs):
        self.thumbnails = thumbnails
        super().__init__(*args, **kwargs)
    
    def to_representation(self, img):
        if img:
            data = {'uri': img.url}
            try:
                data['size'] = (img.width, img.height)
            except FileNotFoundError:
                logger.warning('File not found: %s' % img.path)
                data['size'] = None
            else:
                if self.thumbnails:
                    data['thumbnails'] = {}
                    thbn = get_thumbnailer(img)
                    for alias in self.thumbnails: 
                        try:
                            data['thumbnails'][alias] = thbn.get_thumbnail(
                                settings.THUMBNAIL_ALIASES[''][alias], generate=False).url
                        except AttributeError:
                            pass
            return data


class PartMoveSerializer(serializers.ModelSerializer):
    index = serializers.IntegerField()
    
    class Meta:
        model = DocumentPart
        fields = ('index',)
    
    def __init__(self, *args, part=None, **kwargs):
        self.part = part
        super().__init__(*args, **kwargs)
    
    def move(self):
        self.part.to(self.validated_data['index'])


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ('pk', 'name')


class PartSerializer(serializers.ModelSerializer):
    image = ImageField(thumbnails=['card', 'large'])
    bw_image = ImageField(thumbnails=['large'], required=False)
    workflow = serializers.JSONField(read_only=True)
    transcription_progress = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = DocumentPart
        fields = (
            'pk',
            'name',
            'title',
            'typology',
            'image',
            'bw_image',
            'workflow',
            'recoverable',
            'transcription_progress'
        )
    
    def create(self, data):
        document = Document.objects.get(pk=self.context["view"].kwargs["document_pk"])
        data['document'] = document
        obj = super().create(data)
        # generate card thumbnail right away since we need it
        get_thumbnailer(obj.image).get_thumbnail(settings.THUMBNAIL_ALIASES['']['card'])
        return obj


class BlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Block
        fields = ('pk', 'document_part', 'order', 'box')


class LineTranscriptionSerializer(serializers.ModelSerializer):
    # transcription = TranscriptionSerializer()
    
    class Meta:
        model = LineTranscription
        fields = ('pk', 'line', 'transcription', 'content', 'versions')
        
    def cleanup(self, data):
        return bleach.clean(data, tags=['em', 'strong', 's', 'u'], strip=True)

    def validate_content(self, mode):
        return self.cleanup(self.initial_data.get('content'))


class LineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Line
        fields = ('pk',  'order', 'block', 'box')
    
    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.document_part.recalculate_ordering()
        return instance
    
    def update(self, instance, validated_data):
        instance.document_part.recalculate_ordering()
        return super().update(instance, validated_data)


class DetailedLineSerializer(LineSerializer):
    block = BlockSerializer(required=False)
    transcriptions = LineTranscriptionSerializer(many=True, required=False)
    
    class Meta(LineSerializer.Meta):
        fields = LineSerializer.Meta.fields + ('document_part', 'block', 'transcriptions',)


class PartDetailSerializer(PartSerializer):
    blocks = BlockSerializer(many=True)
    lines = LineSerializer(many=True)
    previous = serializers.SerializerMethodField(source='get_previous')
    next = serializers.SerializerMethodField(source='get_next')
    
    class Meta(PartSerializer.Meta):
        fields = PartSerializer.Meta.fields + (
            'blocks',
            'lines',
            'previous',
            'next')
    
    def get_previous(self, instance):
        prev = DocumentPart.objects.filter(
            document=instance.document, order__lt=instance.order).order_by('-order').first()
        return prev and prev.pk or None
    
    def get_next(self, instance):
        nex = DocumentPart.objects.filter(
            document=instance.document, order__gt=instance.order).order_by('order').first()
        return nex and nex.pk or None
