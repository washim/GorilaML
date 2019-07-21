from flask import (
    Blueprint, render_template
)


def plugin(*args, **kws):
    return Blueprint(*args, **kws)


def output(*args, **kws):
    return render_template(*args, **kws)