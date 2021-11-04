from datetime import date, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.template.loader import render_to_string

from users.models import QuotaEvent, User


class Command(BaseCommand):
    help = 'Send quotas alerts to users by email.'
      
    def handle(self, *args, **options):
        if settings.DISABLE_QUOTAS:
            print('Quotas are disabled on this instance, no need to run this command')
            return

        for user in User.objects.all():
            has_disk_storage = user.has_free_disk_storage()
            has_cpu_minutes = user.has_free_cpu_minutes()
            has_gpu_minutes = user.has_free_gpu_minutes()

            if has_disk_storage and has_cpu_minutes and has_gpu_minutes:
                continue

            disk_storage_usage = user.calc_disk_usage()
            cpu_minutes_usage = user.calc_cpu_usage()
            gpu_minutes_usage = user.calc_gpu_usage()
            events = QuotaEvent.objects.filter(
                user=user,
                reached_disk_storage=None if has_disk_storage else disk_storage_usage,
                reached_cpu=None if has_cpu_minutes else cpu_minutes_usage,
                reached_gpu=None if has_gpu_minutes else gpu_minutes_usage,
                created__gte=date.today() - timedelta(days=settings.QUOTA_NOTIFICATIONS_TIMEOUT)
            )

            reached = [
                None if has_disk_storage else 'Disk storage',
                None if has_cpu_minutes else 'CPU minutes',
                None if has_gpu_minutes else 'GPU minutes',
            ]
            reached = [x for x in reached if x]

            if events:
                reached = ', '.join(reached)
                print(f'The user {user.pk} reached his following quotas: {reached}. An email was already send less than {settings.QUOTA_NOTIFICATIONS_TIMEOUT} days ago.')
                continue

            sent = send_mail(
                subject=f'You have reached one or more of your quotas on eScriptorium',
                message=render_to_string(
                    'users/email/quotas_reached_email.html',
                    context={
                        'user': user,
                        'reached': reached,
                    },
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
            if sent == 0:
                print(f'Failed to send email to {user.pk} to inform him that he reached one or more of his quotas')
                continue

            QuotaEvent.objects.create(
                user=user,
                reached_disk_storage=None if has_disk_storage else disk_storage_usage,
                reached_cpu=None if has_cpu_minutes else cpu_minutes_usage,
                reached_gpu=None if has_gpu_minutes else gpu_minutes_usage
            )
