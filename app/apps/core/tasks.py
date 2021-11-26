import os
import json
import logging
import numpy as np
import os.path
import pathlib
import shutil
from fabric import Connection
from itertools import groupby
from datetime import datetime
from zipfile import ZipFile

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import F, Q, Prefetch
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.template import loader

from celery import shared_task
from celery.signals import before_task_publish, task_prerun, task_success, task_failure, worker_ready
from django_redis import get_redis_connection
from easy_thumbnails.files import get_thumbnailer
from kraken.lib import train as kraken_train

# from core.models import Line
#from core.models import ClusterJob
from users.consumers import send_event

#import core.clusterjob

import time

logger = logging.getLogger(__name__)
User = get_user_model()
redis_ = get_redis_connection()


def update_client_state(part_id, task, status, task_id=None, data=None):
    DocumentPart = apps.get_model('core', 'DocumentPart')
    part = DocumentPart.objects.get(pk=part_id)
    task_name = task.split('.')[-1]
    send_event('document', part.document.pk, "part:workflow", {
        "id": part.pk,
        "process": task_name,
        "status": status,
        "task_id": task_id,
        "data": data or {}
    })


@shared_task(autoretry_for=(MemoryError,), default_retry_delay=60)
def generate_part_thumbnails(instance_pk, user_pk=None, **kwargs):
    if not getattr(settings, 'THUMBNAIL_ENABLE', True):
        return

    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
            # If quotas are enforced, assert that the user still has free CPU minutes
            if not settings.DISABLE_QUOTAS and user.cpu_minutes_limit() != None:
                assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
        except User.DoesNotExist:
            user = None

    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to compress innexistant DocumentPart : %d', instance_pk)
        return

    aliases = {}
    thbnr = get_thumbnailer(part.image)
    for alias, config in settings.THUMBNAIL_ALIASES[''].items():
        aliases[alias] = thbnr.get_thumbnail(config).url
    return aliases


@shared_task(autoretry_for=(MemoryError,), default_retry_delay=3 * 60)
def convert(instance_pk, user_pk=None, **kwargs):
    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
            # If quotas are enforced, assert that the user still has free CPU minutes
            if not settings.DISABLE_QUOTAS and user.cpu_minutes_limit() != None:
                assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
        except User.DoesNotExist:
            user = None

    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to convert innexistant DocumentPart : %d', instance_pk)
        return
    part.convert()


@shared_task(autoretry_for=(MemoryError,), default_retry_delay=5 * 60)
def lossless_compression(instance_pk, user_pk=None, **kwargs):
    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
            # If quotas are enforced, assert that the user still has free CPU minutes
            if not settings.DISABLE_QUOTAS and user.cpu_minutes_limit() != None:
                assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
        except User.DoesNotExist:
            user = None

    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to compress innexistant DocumentPart : %d', instance_pk)
        return
    part.compress()


@shared_task(autoretry_for=(MemoryError,), default_retry_delay=10 * 60)
def binarize(instance_pk, user_pk=None, binarizer=None, threshold=None, **kwargs):
    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to binarize innexistant DocumentPart : %d', instance_pk)
        return

    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
            # If quotas are enforced, assert that the user still has free CPU minutes
            if not settings.DISABLE_QUOTAS and user.cpu_minutes_limit() != None:
                assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
        except User.DoesNotExist:
            user = None
    else:
        user = None

    try:
        part.binarize(threshold=threshold)
    except Exception as e:
        if user:
            user.notify(_("Something went wrong during the binarization!"),
                        id="binarization-error", level='danger')
        part.workflow_state = part.WORKFLOW_STATE_CREATED
        part.save()
        logger.exception(e)
        raise e
    else:
        if user:
            user.notify(_("Binarization done!"),
                        id="binarization-success", level='success')


def make_segmentation_training_data(part):
    data = {
        'image': part.image.path,
        'baselines': [{'script': line.typology and line.typology.name or 'default',
                       'baseline': line.baseline}
                      for line in part.lines.only('baseline', 'typology')
                      if line.baseline],
        'regions':  {typo: list(reg.box for reg in regs)
                     for typo, regs in groupby(
                        part.blocks.only('box', 'typology').order_by('typology'),
                        key=lambda reg: reg.typology and reg.typology.name or 'default')}
    }
    return data


@shared_task(bind=True, autoretry_for=(MemoryError,), default_retry_delay=60 * 60)
def segtrain(task, model_pk, document_pk, part_pks, user_pk=None, **kwargs):
    segtrain_cluster(task, model_pk, document_pk, part_pks, user_pk, **kwargs)


def segtrain_cluster(task, model_pk, document_pk, part_pks, user_pk=None, **kwargs):
    from imports.tasks import write_to_file

    # # Note hack to circumvent AssertionError: daemonic processes are not allowed to have children
    from multiprocessing import current_process
    current_process().daemon = False

    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
        except User.DoesNotExist:
            user = None
    else:
        user = None

    def msg(txt, fg=None, nl=False):
        logger.info(txt)

    redis_.set('segtrain-%d' % model_pk, json.dumps({'task_id': task.request.id}))

    Document = apps.get_model('core', 'Document')
    DocumentPart = apps.get_model('core', 'DocumentPart')
    OcrModel = apps.get_model('core', 'OcrModel')
    Transcription = apps.get_model('core', 'Transcription')

    model = OcrModel.objects.get(pk=model_pk)

    try:
        load = model.file.path
    except ValueError:  # model is empty
        load = settings.KRAKEN_DEFAULT_SEGMENTATION_MODEL
        model.file = model.file.field.upload_to(model, slugify(model.name) + '.mlmodel')

    model_dir = os.path.join(settings.MEDIA_ROOT, os.path.split(model.file.path)[0])

    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    try:
        model.training = True
        model.save()
        send_event('document', document_pk, "training:start", {
            "id": model.pk,
        })
        qs = DocumentPart.objects.filter(pk__in=part_pks).prefetch_related('lines')

        # Writing ground truth data on disk
        # Seems OK to write segments geometry
        # CONTENT is empty in the xml, normal while doing segmentation ?
        document = Document.objects.get(pk=document_pk)
        document.submitting_job = True
        document.save()
        #transcription = Transcription.objects.get(document=document, pk=transcription_pk)
        base_filename = "export_doc%d_%s_%s_%s" % (
            document.pk,
            slugify(document.name).replace('-', '_')[:32],
            "alto",
            datetime.now().strftime('%Y%m%d%H%M'))

        
        gt_filename = "%s.zip" % base_filename
        gt_filepath = os.path.join(user.get_document_store_path(), gt_filename)

        write_to_file(gt_filepath, qs, document)

        print("Written "+gt_filepath)

        # job = core.clusterjob.ClusterJob(username='kuenzlip', 
        #                             cluster_addr='login1.yggdrasil.hpc.unige.ch', 
        #                             workdir='/home/users/k/kuenzlip/celery-workdir/ketos/')

        ClusterJob = apps.get_model('core', 'ClusterJob')


        job = ClusterJob(django_user=user, 
                        ocr_model=model,
                        cluster_username='kuenzlip',
                        cluster_hostname='login1.yggdrasil.hpc.unige.ch',
                        base_workdir='/home/users/k/kuenzlip/celery-workdir/ketos/')

        job.save()
        
        model.cluster_job = job
 
        model.save()
        

        # send_event('document', document_pk, "training:statechange",{
        #     "jobid": "Unknown",
        #     "state": "Sending"
        # })

        # jobid = job.request_segmenter_training(filepath)

        connect_kwargs = {
            'passphrase': os.getenv('SSH_PASSPHRASE')
        }

        connection = Connection(host=job.cluster_hostname,
                                user=job.cluster_username,
                                connect_kwargs=connect_kwargs)
                                

        job.request_segmentation_training(connection, gt_filepath)

        #time.sleep(10)

        # send_event('document', document_pk, "training:statechange",{
        #     "jobid": job.job_id,
        #     "state": job.last_known_state
        # })


        # save job in bdd 
        job.save()

        # launch a monitoring task if necessary, there should be no race condition
        # monitoring_task_counter = redis_.incr('monitoring-task-counter')
        # if monitoring_task_counter == 1:
        #     print('Launching a new monitoring task')
        #     redis_.expire('monitoring-task-counter', 30)
        #     monitor_cluster_jobs.delay()
        # else:
        # else write the task in redis
        print('writing in redis ', job.cluster_hostname+':'+job.job_id)
        redis_.rpush('job-ids', job.cluster_hostname+':'+job.job_id)

        print('Done submitting segtrain job')
        

        # while not job.task_is_complete():
        #     state = job.current_state()
        #     send_event('document', document_pk, "training:statechange",{
        #         "jobid": jobid,
        #         "state": state
        #     })
        #     time.sleep(10)
        
        # send_event('document', document_pk, "training:statechange",{
        #     "jobid": jobid,
        #     "state": "Finished"
        # })

        # print('Training done')

        # best_version = job.result_path()
        # model.training_accuracy = job.best_accuracy()

        # shutil.copy(best_version, model.file.path)

    finally:
        # pass        
        # model.training = False
        # model.save()

        document.submitting_job = False
        document.save()

        send_event('document', document_pk, "training:senddone", {
            "id": model.pk,
            "jobid" : job.job_id,
            "state": job.last_known_state,
            "jobuuid": job.job_uuid,
            "is_finished": str(job.is_finished)
        })
    

#@shared_task(bind=True, autoretry_for=(MemoryError,), default_retry_delay=60 * 60)
def segtrain_local(task, model_pk, document_pk, part_pks, user_pk=None, **kwargs):
    # # Note hack to circumvent AssertionError: daemonic processes are not allowed to have children
    from multiprocessing import current_process
    current_process().daemon = False

    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
            # If quotas are enforced, assert that the user still has free CPU minutes, GPU minutes and disk storage
            if not settings.DISABLE_QUOTAS:
                if user.cpu_minutes_limit() != None:
                    assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
                if user.gpu_minutes_limit() != None:
                    assert user.has_free_gpu_minutes(), f"User {user.id} doesn't have any GPU minutes left"
                if user.disk_storage_limit() != None:
                    assert user.has_free_disk_storage(), f"User {user.id} doesn't have any disk storage left"
        except User.DoesNotExist:
            user = None
    else:
        user = None

    def msg(txt, fg=None, nl=False):
        logger.info(txt)

    redis_.set('segtrain-%d' % model_pk, json.dumps({'task_id': task.request.id}))

    Document = apps.get_model('core', 'Document')
    DocumentPart = apps.get_model('core', 'DocumentPart')
    OcrModel = apps.get_model('core', 'OcrModel')

    model = OcrModel.objects.get(pk=model_pk)

    try:
        load = model.file.path
    except ValueError:  # model is empty
        load = settings.KRAKEN_DEFAULT_SEGMENTATION_MODEL
        model.file = model.file.field.upload_to(model, slugify(model.name) + '.mlmodel')

    model_dir = os.path.join(settings.MEDIA_ROOT, os.path.split(model.file.path)[0])

    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    try:
        model.training = True
        model.save()
        send_event('document', document_pk, "training:start", {
            "id": model.pk,
        })
        qs = DocumentPart.objects.filter(pk__in=part_pks).prefetch_related('lines')

        ground_truth = list(qs)
        if ground_truth[0].document.line_offset == Document.LINE_OFFSET_TOPLINE:
            topline = True
        elif ground_truth[0].document.line_offset == Document.LINE_OFFSET_CENTERLINE:
            topline = None
        else:
            topline = False

        np.random.default_rng(241960353267317949653744176059648850006).shuffle(ground_truth)
        partition = max(1, int(len(ground_truth) / 10))

        training_data = []
        evaluation_data = []
        for part in qs[partition:]:
            training_data.append(make_segmentation_training_data(part))
        for part in qs[:partition]:
            evaluation_data.append(make_segmentation_training_data(part))

        DEVICE = getattr(settings, 'KRAKEN_TRAINING_DEVICE', 'cpu')
        LOAD_THREADS = getattr(settings, 'KRAKEN_TRAINING_LOAD_THREADS', 0)
        trainer = kraken_train.KrakenTrainer.segmentation_train_gen(
            message=msg,
            output=os.path.join(model_dir, 'version'),
            format_type=None,
            device=DEVICE,
            load=load,
            training_data=training_data,
            evaluation_data=evaluation_data,
            threads=LOAD_THREADS,
            augment=True,
            resize='both',
            hyper_params={'epochs': 30},
            load_hyper_parameters=True,
            topline=topline
        )

        def _print_eval(epoch=0, accuracy=0, mean_acc=0, mean_iu=0, freq_iu=0,
                        val_metric=0):
            model.refresh_from_db()
            model.training_epoch = epoch
            model.training_accuracy = float(val_metric)
            # model.training_total = chars
            # model.training_errors = error
            relpath = os.path.relpath(model_dir, settings.MEDIA_ROOT)
            model.new_version(file=f'{relpath}/version_{epoch}.mlmodel')
            model.save()

            send_event('document', document_pk, "training:eval", {
                "id": model.pk,
                'versions': model.versions,
                'epoch': epoch,
                'accuracy': float(val_metric)
                # 'chars': chars,
                # 'error': error
            })

        trainer.run(_print_eval)

        best_version = os.path.join(model_dir,
                                    f'version_{trainer.stopper.best_epoch}.mlmodel')

        try:
            shutil.copy(best_version, model.file.path)  # os.path.join(model_dir, filename)
        except FileNotFoundError as e:
            user.notify(_("Training didn't get better results than base model!"),
                        id="seg-no-gain-error", level='warning')
            shutil.copy(load, model.file.path)

    except Exception as e:
        send_event('document', document_pk, "training:error", {
            "id": model.pk,
        })
        if user:
            user.notify(_("Something went wrong during the segmenter training process!"),
                        id="training-error", level='danger')
        logger.exception(e)
        raise e
    else:
        if user:
            user.notify(_("Training finished!"),
                        id="training-success",
                        level='success')
    finally:
        model.training = False
        model.file_size = model.file.size
        model.save()

        send_event('document', document_pk, "training:done", {
            "id": model.pk,
        })


@shared_task(autoretry_for=(MemoryError,), default_retry_delay=5 * 60)
def segment(instance_pk, user_pk=None, model_pk=None,
            steps=None, text_direction=None, override=None,
            **kwargs):
    """
    steps can be either 'regions', 'lines' or 'both'
    """
    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist as e:
        logger.error('Trying to segment innexistant DocumentPart : %d', instance_pk)
        return

    try:
        OcrModel = apps.get_model('core', 'OcrModel')
        model = OcrModel.objects.get(pk=model_pk)
    except OcrModel.DoesNotExist:
        model = None

    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
            # If quotas are enforced, assert that the user still has free CPU minutes
            if not settings.DISABLE_QUOTAS and user.cpu_minutes_limit() != None:
                assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
        except User.DoesNotExist:
            user = None
    else:
        user = None

    try:
        if steps == 'masks':
            part.make_masks()
        else:
            part.segment(steps=steps,
                         override=override,
                         text_direction=text_direction,
                         model=model)
    except Exception as e:
        if user:
            user.notify(_("Something went wrong during the segmentation!"),
                        id="segmentation-error", level='danger')
        part.workflow_state = part.WORKFLOW_STATE_CONVERTED
        part.save()
        logger.exception(e)
        raise e
    else:
        if user:
            user.notify(_("Segmentation done!"),
                        id="segmentation-success", level='success')


@shared_task(autoretry_for=(MemoryError,), default_retry_delay=60)
def recalculate_masks(instance_pk, user_pk=None, only=None, **kwargs):
    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
            # If quotas are enforced, assert that the user still has free CPU minutes
            if not settings.DISABLE_QUOTAS and user.cpu_minutes_limit() != None:
                assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
        except User.DoesNotExist:
            user = None

    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist as e:
        logger.error('Trying to recalculate masks of innexistant DocumentPart : %d', instance_pk)
        return

    result = part.make_masks(only=only)
    send_event('document', part.document.pk, "part:mask", {
        "id": part.pk,
        "lines": [{'pk': line.pk, 'mask': line.mask} for line in result]
    })


@shared_task(bind=True, autoretry_for=(MemoryError,), default_retry_delay=60 * 60)
def train(task, part_pks, transcription_pk, model_pk, user_pk=None, **kwargs):
    train_cluster(task, part_pks, transcription_pk, model_pk, user_pk, **kwargs)


def train_cluster(task, part_pks, transcription_pk, model_pk, user_pk=None, **kwargs):
    from imports.tasks import write_to_file

    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
        except User.DoesNotExist:
            user = None
    else:
        user = None

    redis_.set('training-%d' % model_pk, json.dumps({'task_id': task.request.id}))

    DocumentPart = apps.get_model('core', 'DocumentPart')
    Document = apps.get_model('core', 'Document')
    Transcription = apps.get_model('core', 'Transcription')
    LineTranscription = apps.get_model('core', 'LineTranscription')
    OcrModel = apps.get_model('core', 'OcrModel')

    try:
        model = OcrModel.objects.get(pk=model_pk)

        load = None
        try:
            load = model.file.path
        except ValueError:  # model is empty
            filename = slugify(model.name) + '.mlmodel'
            model.file = model.file.field.upload_to(model, filename)
            model.save()

        model_dir = os.path.join(settings.MEDIA_ROOT, os.path.split(model.file.path)[0])

        if not os.path.exists(model_dir):
            os.makedirs(model_dir)


        model.training = True
        model.save()
        
        # document = transcription.document
        transcription = Transcription.objects.get(pk=transcription_pk)
        document_pk = transcription.document.pk
        document = Document.objects.get(pk=document_pk)
        document.submitting_job = True
        document.save()
        
        # print("transcription_pk : ", transcription_pk)
        # print("document_pk : ", document_pk)

        send_event('document', document_pk, "training:start", {
            "id": model.pk,
        })
        # qs = (LineTranscription.objects
        #       .filter(transcription=transcription,
        #               line__document_part__pk__in=part_pks)
        #       .exclude(Q(content='') | Q(content=None)))
        qs = DocumentPart.objects.filter(pk__in=part_pks).prefetch_related('lines')

        
        base_filename = "export_doc%d_%s_%s_%s" % (
            document.pk,
            slugify(document.name).replace('-', '_')[:32],
            "alto",
            datetime.now().strftime('%Y%m%d%H%M'))

        
        gt_filename = "%s.zip" % base_filename
        gt_filepath = os.path.join(user.get_document_store_path(), filename)

        write_to_file(gt_filepath, qs, document, transcription=transcription)

        print("Written "+gt_filepath)
        ClusterJob = apps.get_model('core', 'ClusterJob')

        job = ClusterJob(django_user=user, 
                        ocr_model=model,
                        cluster_username='kuenzlip',
                        cluster_hostname='login1.yggdrasil.hpc.unige.ch',
                        base_workdir='/home/users/k/kuenzlip/celery-workdir/ketos/')

        job.save()
        
        model.cluster_job = job
 
        model.save()

        connect_kwargs = {
            'passphrase': os.getenv('SSH_PASSPHRASE')
        }

        connection = Connection(host=job.cluster_hostname,
                                user=job.cluster_username,
                                connect_kwargs=connect_kwargs)

        job.request_recognition_training(connection, gt_filepath)

        job.save()

        print('writing in redis ', job.cluster_hostname+':'+job.job_id)
        redis_.rpush('job-ids', job.cluster_hostname+':'+job.job_id)

        print('Done submitting train job')

        # while not job.task_is_complete():
        #     time.sleep(10)
        
        # print('Training done')

        # best_version = job.result_path()

        # print('best version file : '+best_version)

        # model.training_accuracy = job.best_accuracy()

        # shutil.copy(best_version, model.file.path)


    # except Exception as e:
    #     send_event('document', document.pk, "training:error", {
    #         "id": model.pk,
    #     })
    #     if user:
    #         user.notify(_("Something went wrong during the training process!"),
    #                     id="training-error", level='danger')
    #     logger.exception(e)
    # else:
    #     if user:
    #         user.notify(_("Training finished!"),
    #                     id="training-success",
    #                     level='success')
    finally:
        # model.training = False
        # model.save()

        document.submitting_job = False
        document.save()

        send_event('document', document_pk, "training:senddone", {
            "id": model.pk,
            "jobid" : job.job_id,
            "state": job.last_known_state,
            "jobuuid": job.job_uuid,
            "is_finished": str(job.is_finished)
        })



def train_(qs, document, transcription, model=None, user=None):

    # # Note hack to circumvent AssertionError: daemonic processes are not allowed to have children
    from multiprocessing import current_process
    current_process().daemon = False

    # try to minimize what is loaded in memory for large datasets
    ground_truth = list(qs.values('content',
                                  baseline=F('line__baseline'),
                                  mask=F('line__mask'),
                                  image=F('line__document_part__image')))

    np.random.default_rng(241960353267317949653744176059648850006).shuffle(ground_truth)

    partition = int(len(ground_truth) / 10)

    training_data = [{'image': os.path.join(settings.MEDIA_ROOT, lt['image']),
                      'text': lt['content'],
                      'baseline': lt['baseline'],
                      'boundary': lt['mask']} for lt in ground_truth[partition:]]
    evaluation_data = [{'image': os.path.join(settings.MEDIA_ROOT, lt['image']),
                        'text': lt['content'],
                        'baseline': lt['baseline'],
                        'boundary': lt['mask']} for lt in ground_truth[:partition]]

    load = None
    try:
        load = model.file.path
    except ValueError:  # model is empty
        filename = slugify(model.name) + '.mlmodel'
        model.file = model.file.field.upload_to(model, filename)
        model.save()

    model_dir = os.path.join(settings.MEDIA_ROOT, os.path.split(model.file.path)[0])

    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    DEVICE = getattr(settings, 'KRAKEN_TRAINING_DEVICE', 'cpu')
    LOAD_THREADS = getattr(settings, 'KRAKEN_TRAINING_LOAD_THREADS', 0)
    trainer = (kraken_train.KrakenTrainer
               .recognition_train_gen(device=DEVICE,
                                      load=load,
                                      output=os.path.join(model_dir, 'version'),
                                      format_type=None,
                                      training_data=training_data,
                                      evaluation_data=evaluation_data,
                                      resize='add',
                                      threads=LOAD_THREADS,
                                      augment=True,
                                      hyper_params={'batch_size': 1},
                                      load_hyper_parameters=True))

    def _print_eval(epoch=0, accuracy=0, chars=0, error=0, val_metric=0):
        model.refresh_from_db()
        model.training_epoch = epoch
        model.training_accuracy = accuracy
        model.training_total = int(chars)
        model.training_errors = error
        relpath = os.path.relpath(model_dir, settings.MEDIA_ROOT)
        model.new_version(file=f'{relpath}/version_{epoch}.mlmodel')
        model.save()

        send_event('document', document.pk, "training:eval", {
            "id": model.pk,
            'versions': model.versions,
            'epoch': epoch,
            'accuracy': accuracy,
            'chars': int(chars),
            'error': error})

    trainer.run(_print_eval)
    best_version = os.path.join(model_dir, f'version_{trainer.stopper.best_epoch}.mlmodel')
    shutil.copy(best_version, model.file.path)


# @shared_task(bind=True, autoretry_for=(MemoryError,), default_retry_delay=60 * 60)
def train_local(task, part_pks, transcription_pk, model_pk, user_pk=None, **kwargs):

    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
            # If quotas are enforced, assert that the user still has free CPU minutes, GPU minutes and disk storage
            if not settings.DISABLE_QUOTAS:
                if user.cpu_minutes_limit() != None:
                    assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
                if user.gpu_minutes_limit() != None:
                    assert user.has_free_gpu_minutes(), f"User {user.id} doesn't have any GPU minutes left"
                if user.disk_storage_limit() != None:
                    assert user.has_free_disk_storage(), f"User {user.id} doesn't have any disk storage left"
        except User.DoesNotExist:
            user = None
    else:
        user = None

    redis_.set('training-%d' % model_pk, json.dumps({'task_id': task.request.id}))

    Transcription = apps.get_model('core', 'Transcription')
    LineTranscription = apps.get_model('core', 'LineTranscription')
    OcrModel = apps.get_model('core', 'OcrModel')

    try:
        model = OcrModel.objects.get(pk=model_pk)
        model.training = True
        model.save()
        transcription = Transcription.objects.get(pk=transcription_pk)
        document = transcription.document
        send_event('document', document.pk, "training:start", {
            "id": model.pk,
        })
        qs = (LineTranscription.objects
              .filter(transcription=transcription,
                      line__document_part__pk__in=part_pks)
              .exclude(Q(content='') | Q(content=None)))
        train_(qs, document, transcription, model=model, user=user)
    except Exception as e:
        send_event('document', document.pk, "training:error", {
            "id": model.pk,
        })
        if user:
            user.notify(_("Something went wrong during the training process!"),
                        id="training-error", level='danger')
        logger.exception(e)
    else:
        if user:
            user.notify(_("Training finished!"),
                        id="training-success",
                        level='success')
    finally:
        model.training = False
        model.file_size = model.file.size
        model.save()

        send_event('document', document.pk, "training:done", {
            "id": model.pk,
        })


@shared_task(autoretry_for=(MemoryError,), default_retry_delay=10 * 60)
def transcribe(instance_pk, model_pk=None, user_pk=None, text_direction=None, **kwargs):

    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:

        logger.error('Trying to transcribe innexistant DocumentPart : %d', instance_pk)
        return

    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
            # If quotas are enforced, assert that the user still has free CPU minutes
            if not settings.DISABLE_QUOTAS and user.cpu_minutes_limit() != None:
                assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
        except User.DoesNotExist:
            user = None
    else:
        user = None

    try:
        OcrModel = apps.get_model('core', 'OcrModel')
        model = OcrModel.objects.get(pk=model_pk)
        part.transcribe(model)
    except Exception as e:
        if user:
            user.notify(_("Something went wrong during the transcription!"),
                        id="transcription-error", level='danger')
        part.workflow_state = part.WORKFLOW_STATE_SEGMENTED
        part.save()
        logger.exception(e)
        raise e
    else:
        if user and model:
            user.notify(_("Transcription done!"),
                        id="transcription-success",
                        level='success')


def check_signal_order(old_signal, new_signal):
    SIGNAL_ORDER = ['before_task_publish', 'task_prerun', 'task_failure', 'task_success']
    return SIGNAL_ORDER.index(old_signal) < SIGNAL_ORDER.index(new_signal)


@before_task_publish.connect
def before_publish_state(sender=None, body=None, **kwargs):
    if not sender.startswith('core.tasks') or sender.endswith('train') or sender.endswith('monitor_cluster_jobs'):
        return
    instance_id = body[0][0]
    data = json.loads(redis_.get('process-%d' % instance_id) or '{}')

    signal_name = kwargs['signal'].name

    try:
        # protects against signal race condition
        if (data[sender]['task_id'] == sender.request.id and
            not check_signal_order(data[sender]['status'], signal_name)):
            return
    except (KeyError, AttributeError):
        pass

    data[sender] = {
        "task_id": kwargs['headers']['id'],
        "status": 'before_task_publish'
    }
    redis_.set('process-%d' % instance_id, json.dumps(data))
    try:
        update_client_state(instance_id, sender, 'pending')
    except NameError:
        pass


@task_prerun.connect
@task_success.connect
@task_failure.connect
def done_state(sender=None, body=None, **kwargs):
    if not sender.name.startswith('core.tasks') or sender.name.endswith('train') or sender.name.endswith('monitor_cluster_jobs'):
        return
    instance_id = sender.request.args[0]

    try:
        data = json.loads(redis_.get('process-%d' % instance_id) or '{}')
    except TypeError as e:
        logger.exception(e)
        return

    signal_name = kwargs['signal'].name

    try:
        # protects against signal race condition
        if (data[sender.name]['task_id'] == sender.request.id and
            not check_signal_order(data[sender.name]['status'], signal_name)):
            return
    except KeyError:
        pass

    data[sender.name] = {
        "task_id": sender.request.id,
        "status": signal_name
    }
    status = {
        'task_success': 'done',
        'task_failure': 'error',
        'task_prerun': 'ongoing'
    }[signal_name]
    if status == 'error':
        # remove any pending task down the chain
        data = {k: v for k, v in data.items() if v['status'] != 'pending'}
    redis_.set('process-%d' % instance_id, json.dumps(data))

    if status == 'done':
        result = kwargs.get('result', None)
    else:
        result = None
    update_client_state(instance_id, sender.name, status, task_id=sender.request.id, data=result)


def new_jobs_to_monitor():
    jobref = redis_.lpop('job-ids')
    new_jobs = {}
    ClusterJob = apps.get_model('core', 'ClusterJob')
    while jobref:
        jobref = jobref.decode("utf-8")
        cluster_hostname = jobref.split(':')[0]
        job_id = jobref.split(':')[1]
        print('found job ' + cluster_hostname + ':' + job_id)

        job = ClusterJob.objects.get(cluster_hostname=cluster_hostname, job_id=job_id)
        new_jobs[jobref] = job

        jobref = redis_.lpop('job-ids')
    return new_jobs


def establish_connections(jobs, existing_connections):
    connect_kwargs = {
        'passphrase': os.getenv('SSH_PASSPHRASE')
    }
    for job_name in jobs:
        job = jobs[job_name]
        if job_name not in existing_connections:
            existing_connections[job.cluster_hostname+':'+job.cluster_username] = Connection(host=job.cluster_hostname,
                                                                                            user=job.cluster_username,
                                                                                            connect_kwargs=connect_kwargs)
    return existing_connections


@shared_task(autoretry_for=(MemoryError,), default_retry_delay=10 * 60)
@worker_ready.connect
def launch_monitor_cluster_jobs(**kwargs):
    monitor_cluster_jobs.delay()


@shared_task(autoretry_for=(MemoryError,), default_retry_delay=10 * 60)
def monitor_cluster_jobs(**kwargs):
    #jobs = []
    # load unfinished jobs from bdd
    ClusterJob = apps.get_model('core', 'ClusterJob')

    jobs = {}
    jobs_queryset = ClusterJob.objects.filter(is_finished=False)
    jobs_queryset_list = list(jobs_queryset)
    #print('job queryset list : ', jobs_queryset_list)
    for job in jobs_queryset_list:
        jobs[job.cluster_hostname+':'+job.job_id] = job

    print(jobs)

    connections = establish_connections(jobs, {})

    #for i in range(1):
    while True:

        #print('Monitoring !')


        # pop new jobs to monitor from redis

        # pull new jobs from bdd into in memory job pool

        new_jobs = new_jobs_to_monitor()
        jobs.update(new_jobs)
        connections = establish_connections(new_jobs, connections)

        

        print(str(len(jobs))+' jobs monitored :')

        jobs_to_delete = []

        #print(jobs)
        for job_name in jobs:
            job = jobs[job_name]
            connection_name = job.cluster_hostname+':'+job.cluster_username
            connection = connections[connection_name]
            state_changed = job.update_state(connection)
            print(job.cluster_hostname + ':' + job.job_id + ' ' +job.last_known_state)
            if state_changed:
                for doc in job.ocr_model.documents.all():
                    send_event('document', doc.pk, "training:statechange",{
                                "id": job.ocr_model.pk,
                                "state": job.last_known_state,
                                "is_finished": str(job.is_finished)
                    })
                job.save()
            if 'COMPLETED' in job.last_known_state or 'CANCELLED' in job.last_known_state or 'TIMEOUT' in job.last_known_state or 'OUT_OF_MEMORY' in job.last_known_state or job.job_id=='':
                try:
                    best_version_path = job.download_result(connection)
                    shutil.copy(best_version_path, job.ocr_model.file.path)
                    job.ocr_model.training_accuracy = job.best_accuracy(connection)
                except:
                    print('Error occured in retrieving data')
                finally:

                    job.is_finished = True
                    job.ocr_model.training = False
                    job.ocr_model.save()
                    job.save()

                    for doc in job.ocr_model.documents.all():
                        send_event('document', doc.pk, "training:done", {
                            "id": job.ocr_model.pk,
                            "accuracy": str(job.ocr_model.training_accuracy),
                            "is_finished": str(job.is_finished)
                        })

                    jobs_to_delete.append(job_name)

    
        for job_name in jobs_to_delete:
            del jobs[job_name]

        # print(str(len(connections)) + ' connections established :')
        # for key in connections:
        #     print(key)


        # request cluster for job states

        # update job state in bdd if necessary

        # download results if necessary (and if possible)

        # remove jobs from in memory job pool if necessary

        # redis_.expire('monitoring-task-counter', 30)
        time.sleep(10)

