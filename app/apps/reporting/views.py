from datetime import date, timedelta
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import DurationField, ExpressionWrapper, F
from django.views.generic import ListView, DetailView

from reporting.models import TaskReport
from users.models import MEGABYTES_TO_BYTES, User


class ReportList(LoginRequiredMixin, ListView):
    model = TaskReport
    paginate_by = 20

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        cpu_usage = self.request.user.calc_cpu_usage()
        context['cpu_cost_last_week'] = cpu_usage
        gpu_usage = self.request.user.calc_gpu_usage()
        context['gpu_cost_last_week'] = gpu_usage
        
        disk_storage_limit = self.request.user.disk_storage_limit()
        context['enforce_disk_storage'] = not settings.DISABLE_QUOTAS and disk_storage_limit != None
        if context['enforce_disk_storage']:
            context['disk_storage_used_percentage'] = min(round((self.request.user.calc_disk_usage()*100)/disk_storage_limit, 2) if disk_storage_limit else 100, 100)
        
        cpu_minutes_limit = self.request.user.cpu_minutes_limit()
        context['enforce_cpu'] = not settings.DISABLE_QUOTAS and cpu_minutes_limit != None
        if context['enforce_cpu']:
            context['cpu_minutes_used_percentage'] = min(round((cpu_usage*100)/cpu_minutes_limit, 2) if cpu_minutes_limit else 100, 100)
        
        gpu_minutes_limit = self.request.user.gpu_minutes_limit()
        context['enforce_gpu'] = not settings.DISABLE_QUOTAS and gpu_minutes_limit != None
        if context['enforce_gpu']:
            context['gpu_minutes_used_percentage'] = min(round((gpu_usage*100)/gpu_minutes_limit, 2) if gpu_minutes_limit else 100, 100)

        return context

    def get_queryset(self):
        qs = super().get_queryset()

        blacklist = [
            'core.tasks.lossless_compression',
            'core.tasks.convert',
            'core.tasks.generate_part_thumbnails',
            'users.tasks.async_email',
            'core.tasks.recalculate_masks'
        ]

        return (qs.filter(user=self.request.user)
                  .exclude(method__in=blacklist)
                  .annotate(duration=ExpressionWrapper(F('done_at') - F('started_at'),
                                                       output_field=DurationField()))
                  .order_by('-queued_at'))


class ReportDetail(LoginRequiredMixin, DetailView):
    model = TaskReport
    context_object_name = 'report'

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)


class QuotasLeaderboard(LoginRequiredMixin, ListView):
    model = User
    template_name = "reporting/quotas_leaderboard.html"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        today = date.today()
        last_week = today - timedelta(days=7)
        last_day = today - timedelta(days=1)

        having_clause = ""
        only_display_exceeded = self.request.GET.get('display_exceeded', 'off') in ('on', 'ON')
        if only_display_exceeded and not settings.DISABLE_QUOTAS:
            # HAVING clause to exclude users that still have free usage in all of their quotas
            having_clause = """
                HAVING
                    (
                        (COALESCE(users_user.quota_disk_storage, %(settings_disk_storage)s) * %(mb_to_b)s) IS NOT NULL 
                        AND (
                            (
                                SELECT
                                    COALESCE(SUM(file_size), 0)
                                FROM
                                    core_ocrmodel
                                WHERE
                                    core_ocrmodel.owner_id = users_user.id
                            ) + (
                                SELECT
                                    COALESCE(SUM(image_file_size), 0)
                                FROM
                                    core_document
                                    LEFT JOIN core_documentpart ON core_documentpart.document_id = core_document.id
                                WHERE
                                    core_document.owner_id = users_user.id
                            )
                        ) >= (COALESCE(users_user.quota_disk_storage, %(settings_disk_storage)s) * %(mb_to_b)s)
                    )
                    OR (
                        COALESCE(users_user.quota_cpu, %(settings_cpu_minutes)s) IS NOT NULL
                        AND
                            COALESCE(SUM(reporting_taskreport.cpu_cost) FILTER (WHERE reporting_taskreport.started_at >= %(last_week)s), 0)
                            >= COALESCE(users_user.quota_cpu, %(settings_cpu_minutes)s)
                    )
                    OR (
                        COALESCE(users_user.quota_gpu, %(settings_gpu_minutes)s) IS NOT NULL
                        AND
                            COALESCE(SUM(reporting_taskreport.gpu_cost) FILTER (WHERE reporting_taskreport.started_at >= %(last_week)s),0)
                            >= COALESCE(users_user.quota_gpu, %(settings_gpu_minutes)s)
                    )
            """
    
        results = qs.raw(
            f"""
            SELECT
                users_user.id,
                users_user.username,
                COALESCE(SUM(reporting_taskreport.cpu_cost), 0) AS total_cpu_usage,
                COALESCE(SUM(reporting_taskreport.gpu_cost), 0) AS total_gpu_usage,
                COALESCE(SUM(reporting_taskreport.cpu_cost) FILTER (WHERE reporting_taskreport.started_at >= %(last_week)s), 0) AS last_week_cpu_usage,
                COALESCE(SUM(reporting_taskreport.gpu_cost) FILTER (WHERE reporting_taskreport.started_at >= %(last_week)s), 0) AS last_week_gpu_usage,
                COUNT(reporting_taskreport.id) AS total_tasks,
                SUM((reporting_taskreport.done_at - reporting_taskreport.started_at)) AS total_runtime,
                COUNT(reporting_taskreport.id) FILTER (WHERE reporting_taskreport.started_at >= %(last_week)s) AS last_week_tasks,
                SUM((reporting_taskreport.done_at - reporting_taskreport.started_at)) FILTER (WHERE reporting_taskreport.started_at >= %(last_week)s) AS last_week_runtime,
                COUNT(reporting_taskreport.id) FILTER (WHERE reporting_taskreport.started_at >= %(last_day)s) AS last_day_tasks,
                SUM((reporting_taskreport.done_at - reporting_taskreport.started_at)) FILTER (WHERE reporting_taskreport.started_at >= %(last_day)s) AS last_day_runtime,
                (
                    (
                        SELECT
                            COALESCE(SUM(file_size), 0)
                        FROM
                            core_ocrmodel
                        WHERE
                            core_ocrmodel.owner_id = users_user.id
                    ) + (
                        SELECT
                            COALESCE(SUM(image_file_size), 0)
                        FROM
                            core_document
                            LEFT JOIN core_documentpart ON core_documentpart.document_id = core_document.id
                        WHERE
                            core_document.owner_id = users_user.id
                    )
                ) AS disk_usage,
                COALESCE(users_user.quota_disk_storage, %(settings_disk_storage)s) * %(mb_to_b)s AS disk_storage_limit,
                COALESCE(users_user.quota_cpu, %(settings_cpu_minutes)s) AS cpu_minutes_limit,
                COALESCE(users_user.quota_gpu, %(settings_gpu_minutes)s) AS gpu_minutes_limit
            FROM
                users_user
                LEFT JOIN reporting_taskreport ON reporting_taskreport.user_id = users_user.id
            GROUP BY
                users_user.id
            {having_clause}
            ORDER BY
                SUM((reporting_taskreport.done_at - reporting_taskreport.started_at)) DESC NULLS LAST;
            """,
            {
                "last_week": last_week,
                "last_day": last_day,
                "mb_to_b": MEGABYTES_TO_BYTES,
                "settings_disk_storage": settings.QUOTA_DISK_STORAGE,
                "settings_cpu_minutes": settings.QUOTA_CPU_MINUTES,
                "settings_gpu_minutes": settings.QUOTA_GPU_MINUTES
            }
        )

        return results

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['enforce_quotas'] = not settings.DISABLE_QUOTAS
        return context
