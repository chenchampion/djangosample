try:
    from django.utils import simplejson as json
except:
    import simplejson as json
from django.http import HttpResponse
from helpers import *
from models import *


def show_task(request, project_name, task_id):
    project = get_project(request, project_name)
    task = Task.objects.get(project = project, id = task_id)
    return HttpResponse(json.dumps(task.name))