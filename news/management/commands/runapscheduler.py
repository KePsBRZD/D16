import logging
import os
from django.conf import settings
from django.contrib.auth.models import User
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django.core.management.base import BaseCommand, CommandError
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
from news.models import Post, Subscribers, Category
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail

# python manage.py runapscheduler 1 2 3 4

logger = logging.getLogger(__name__)


# наша задача по выводу текста на экран
def my_job():
    some_day_last_week = timezone.now().date() - timedelta(days=7)
    post = Post.objects.filter(created__gt=some_day_last_week)
    user = Subscribers.objects.all()
    user_list = []
    for u in user:
        if u.user not in user_list:
            user_list.append(u.user)
    for u in user_list:
        news_list = []
        for p in post:
            cats = Post.get_category_id(p)
            for c in cats:
                if Subscribers.objects.filter(cats_id=c, user_id=u.pk):
                    if p.title not in news_list:
                        news_list.append(p.title)

        email = User.objects.get(pk=u.pk)
        em = []
        em.append(email.email)
        send_mail(
            subject='Список новых статей, появившийся за неделю!',
            message="\n ".join(news_list),
            from_email='snewsportal@yandex.by',
            recipient_list=em
        )

    # функция, которая будет удалять неактуальные задачи


def delete_old_job_executions(max_age=604_800):
    """This job deletes all apscheduler job executions older than `max_age` from the database."""
    DjangoJobExecution.objects.delete_old_job_executions(max_age)


class Command(BaseCommand):
    help = "Runs apscheduler."

    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), "default")

        # добавляем работу нашему задачнику
        scheduler.add_job(
            my_job,
            trigger=CronTrigger(second="*/10"),
            # То же, что и интервал, но задача тригера таким образом более понятна django
            id="my_job",  # уникальный айди
            max_instances=1,
            replace_existing=True,
        )
        logger.info("Added job 'my_job'.")

        scheduler.add_job(
            delete_old_job_executions,
            trigger=CronTrigger(
                day_of_week="mon", hour="00", minute="00"
            ),
            # Каждую неделю будут удаляться старые задачи, которые либо не удалось выполнить, либо уже выполнять не надо.
            id="delete_old_job_executions",
            max_instances=1,
            replace_existing=True,
        )
        logger.info(
            "Added weekly job: 'delete_old_job_executions'."
        )

        try:
            logger.info("Starting scheduler...")
            scheduler.start()
        except KeyboardInterrupt:
            logger.info("Stopping scheduler...")
            scheduler.shutdown()
            logger.info("Scheduler shut down successfully!")


#        class Command1(BaseCommand):
 #          help = 'Подсказка вашей команды'
#
 #           def add_arguments(self, parser):
  #              parser.add_argument('category', type=str)

   #         def handle(self, *args, **options):
    #            answer = input(f'Вы правда хотите удалить все статьи в категории {options["category"]}? yes/no')
     #
      #          if answer != 'yes':
       #             self.stdout.write(self.style.ERROR('Отменено'))
        #
         #       try:
          #          category = Category.get(name=options['category'])
           #         Post.objects.filter(category == category).delete()
            #        self.stdout.write(self.style.SUCCESS(
             #           f'Succesfully deleted all news from category {category.name}'))  # в случае неправильного подтверждения говорим, что в доступе отказано
              #  except Post.DoesNotExist:
               #     self.stdout.write(self.style.ERROR(f'Could not find category {category.name}'))