from time import localtime, strftime
from Webapp_Portfolio import mongo as mo
from Webapp_Portfolio import functions as mo_f
from django.shortcuts import render, redirect
from django.shortcuts import resolve_url
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from .forms import PortfolioUserCreationForm, PortfolioAuthenticationForm


def message(msg):
    print('    '+str(msg))


def index(request):
    time = strftime("%b %d, %Y %H:%M", localtime())
    login = str(request.user)
    try:
        umid = int(login)
        mongo_user = mo.User(umid)
    except ValueError:
        mongo_user = mo.User(0)   # on Log Out
    except TypeError:
        messages.error(request, 'Your Student ID not in database. Please speak to your professor.')
        mongo_user = mo.User(0)

    # Webapp_Portfolio/templates/Webapp_Portfolio/home.html
    return render(request, 'Webapp_Portfolio/long.html', context={  # input dict after "," to pass jinja values
            'datetime': time,
            'mongo_user': mongo_user,
                }
            )


def register(request):
    if request.method == 'POST':
        form = PortfolioUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'New account created: {username}')
            login(request, user)
            messages.info(request, f'You are now logged in as {username}')
            return redirect('webapp:index')  # to local app's urls.py
        else:
            for msg in form.error_messages:
                messages.error(request, f'{msg}: {form.error_messages[msg]}')
    form = PortfolioUserCreationForm()
    return render(request, 'Webapp_Portfolio/register.html', context={'form': form})


def login_request(request):
    if request.method == 'POST':
        form = PortfolioAuthenticationForm(request, request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"You are now logged in as {username}")
                return redirect('webapp:index')  # to local app's urls.py
            else:
                messages.error(request, 'Invalid student ID or password')
        else:
            messages.error(request, 'Invalid student ID or password')

    form = PortfolioAuthenticationForm()
    return render(request, "Webapp_Portfolio/login.html", {"form": form})


def logout_request(request):
    logout(request)
    messages.info(request, "Logged out successfully!")
    return redirect("webapp:index")


def trade(request):
    if request.method == "POST":
        try:
            umid = int(str(request.user))
        except ValueError:
            messages.error(request, 'Your login is not your Student ID. Please register with UMID.')
        else:
            tradeable_id = list(request.POST)[1]
            try:
                amount = float(request.POST[tradeable_id])
            except ValueError:
                messages.error(request, 'Empty trade.')
            else:
                if 'currencies' in tradeable_id.lower():
                    tradeable_id = tradeable_id[:-3].lower() + tradeable_id[-3:].upper()
                else:
                    tradeable_id = tradeable_id.lower()

                mo_f.buy_commodity(umid=umid, id1=tradeable_id, val1=amount)
        return redirect(f"{resolve_url('webapp:index')}#balance")


def instructor(request):
    time = strftime("%b %d, %Y %H:%M", localtime())
    login = str(request.user)
    if login in ['instructor']:
        ranking_data = list(mo.current_rankings.find({}, {'_id': 0}))
        return render(request, 'Webapp_Portfolio/instructor.html', context={  # dict after "," to pass jinja values
            'datetime': time,
            'ranking_data': ranking_data,
        })
    else:
        print('not an instructor!')
        return redirect('webapp:index')
