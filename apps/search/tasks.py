from celery import shared_task
from django.core.management import call_command


@shared_task(queue="default")
def resync_search_index():
    call_command("search_index", "--populate", "-f")
