import logging
import cgi

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.utils import simplejson
from django.core.urlresolvers import reverse
from django import forms

from google.appengine.api import users

from models import Account
from utils import log_exception
from logic import Eval, SymPyGamma
from network import JSONRPCService, jsonremote

import settings

def login_required(func):
  """Decorator that redirects to the login page if you're not logged in."""

  def login_wrapper(request, *args, **kwds):
    if request.user is None:
      return HttpResponseRedirect(
          users.create_login_url(request.get_full_path().encode('utf-8')))
    return func(request, *args, **kwds)

  login_wrapper.__name__ = func.__name__
  return login_wrapper


class SearchForm(forms.Form):
    i = forms.CharField(required=False)

class SettingsForm(forms.Form):
    show_prompts = forms.BooleanField(required=False)
    join_nonempty_fields = forms.BooleanField(required=False)

def get_user_info(request, logout_go_main=False, settings_active=""):
    user = users.get_current_user()
    if user:
        if logout_go_main:
            logout_url = users.create_logout_url("/")
        else:
            logout_url = users.create_logout_url(request.get_full_path()
                    .encode('utf-8'))
        return '<span class="email">%s</span>|<a class="%s" "href="/settings/">Settings</a>|<a href="%s">Sign out</a>' % \
                (user.email(), settings_active, logout_url)
    else:
        return '<a href="%s">Sign in</a>' % \
                users.create_login_url(request.get_full_path().encode('utf-8'))

def index(request):
    form = SearchForm()
    return render_to_response("index.html", {
        "form": form,
        "MEDIA_URL": settings.MEDIA_URL,
        "main_active": "selected",
        "user_info": get_user_info(request),
        })

def input(request):
    if request.method == "GET":
        form = SearchForm(request.GET)
        if form.is_valid():
            input = form.cleaned_data["i"]
            g = SymPyGamma()
            r = g.eval(input)
            return render_to_response("result.html", {
                "input": input,
                "result": r,
                "form": form,
                "MEDIA_URL": settings.MEDIA_URL,
                "user_info": get_user_info(request),
                })

def notebook(request):
    account = Account.current_user_account
    if account:
        show_prompts = account.show_prompts
        join_nonempty_fields = account.join_nonempty_fields
    else:
        show_prompts = False
        join_nonempty_fields = True
    return render_to_response("nb.html", {
        "MEDIA_URL": settings.MEDIA_URL,
        "nb_active": "selected",
        "user_info": get_user_info(request),
        "show_prompts": show_prompts,
        "join_nonempty_fields": join_nonempty_fields,
        })

def about(request):
    return render_to_response("about.html", {
        "MEDIA_URL": settings.MEDIA_URL,
        "about_active": "selected",
        "user_info": get_user_info(request),
        })

@login_required
def settings_view(request):
    account = Account.current_user_account
    if request.method != "POST":
        form = SettingsForm(initial={
            'show_prompts': account.show_prompts,
            'join_nonempty_fields': account.join_nonempty_fields,
            })
        return render_to_response("settings.html", {
            "form": form,
            "MEDIA_URL": settings.MEDIA_URL,
            "user_info": get_user_info(request, logout_go_main=True,
                settings_active="selected"),
            "account": Account.current_user_account,
            })
    form = SettingsForm(request.POST)
    if form.is_valid():
        account.show_prompts = form.cleaned_data.get('show_prompts')
        account.join_nonempty_fields = \
            form.cleaned_data.get('join_nonempty_fields')
        account.put()
    else:
        HttpResponseRedirect(reverse(settings_view))
    return HttpResponseRedirect(reverse(index))


e = Eval()


testservice = JSONRPCService()


# ---------------------------------
# A few demo services for testing:

@jsonremote(testservice)
def echo(request, msg):
    return msg

@jsonremote(testservice)
def add(request, a, b):
    return a+b

@jsonremote(testservice)
def reverse(request, msg):
    return msg[::-1]

@jsonremote(testservice)
def uppercase(request, msg):
    return msg.upper()

@jsonremote(testservice)
def lowercase(request, msg):
    return msg.lower()

# ---------------------------------

@jsonremote(testservice)
@log_exception
def eval_cell(request, code):
    r = e.eval(code)
    return r

@jsonremote(testservice)
@log_exception
#@login_required
def add_cell(request, insert_before_id=None):
    # comment out the login stuff for now:
    #if request.user is None:
    #        return "no user"
    #    else:
    #        return "X" + str(insert_before_id)
    return "X" + str(insert_before_id)
