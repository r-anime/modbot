"""Utilities regarding Reddit posts/users/etc"""


def slug(submission):
    return submission.permalink.rsplit('/')[-2]
