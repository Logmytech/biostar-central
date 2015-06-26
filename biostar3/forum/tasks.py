from __future__ import absolute_import, division, print_function, unicode_literals

import json
from itertools import *

from celery import shared_task

from .models import *
from . import auth, mailer
from biostar3.utils.compat import *


@shared_task
def compute_user_flair(user):
    """
    This is a fairly compute intensive task. Also the
    flair does not change noticably in short periods of time.
    """


@shared_task
def add_user_location(ip, user):
    """
    Attempts to fill in missing user location.
    """

    if not user.profile.location:
        try:
            url = "http://api.hostip.info/get_json.php?ip=%s" % ip
            logger.info("%s, %s, %s" % (ip, user, url))
            fp = urlopen(url, timeout=3)
            data = fp.read().decode("utf-8")
            data = json.loads(data)
            fp.close()
            location = data.get('country_name', '').title()
            if "unknown" not in location.lower():
                user.profile.location = location
                user.profile.save()
        except KeyError as exc:
            logger.error(exc)


@shared_task
def notify_user(user, post):
    pass



@shared_task
def create_messages(post):
    """
    Generates messages and emails on a post.
    Invoked on each post creation. Will send emails in an internal loop.
    """

    def select_subs(**kwargs):
        # Shortcut to filter post subscriptions.
        subs = PostSub.objects.filter(post=post.root, **kwargs).select_related("user")
        return subs

    def get_user(sub):
        # Returns the user from a subscription.
        return sub.user

    def wants_email(user):
        # Selects users that have chosen email notifications.
        return not (user.profile.message_prefs == settings.LOCAL_TRACKER)

    # All subscribed users that subscribe to the post.
    all_subs = select_subs()
    all_subs = map(get_user, all_subs)

    # Find the users mentioned by handle.
    handler = html.find_users_by_handle(post)

    # Find users that watch this tag.
    watchers = map(get_user, [])

    # The list of all users that will get notifications.
    all_targets = chain(all_subs, handler, all_subs, watchers)
    all_targets = list(all_targets)

    # Find users that want email.
    email_targets = filter(wants_email, all_targets)

    # No need to send notifications to post creator.
    local_targets = set(all_targets)
    email_targets = set(email_targets)

    if post.author in local_targets:
        local_targets.remove(post.author)

    mailer.post_notifications(post, local_targets=local_targets,
                              email_targets=email_targets)

@shared_task
def add(x, y):
    return x + y