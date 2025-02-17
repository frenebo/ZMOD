"""zmk URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from django.conf.urls import *
from django.conf import settings

from rest_framework.documentation import include_docs_urls


from nyokaserver.nyokaServerClass import create_lock
from nyokaserver.nyokaServerClass import NyokaServer
from trainModel.views import RunningTaskView,TrainAutoMLView,RunningTaskOperationView,TrainNNView, ModelCompileView,MRCNNView

from nyokaserver.views import PMMLView,PMMLOpeartionView,PMMLLayerView,PMMLGlobalView
from scoring.views import ScoreView,ModelsView,ModelOperationView,ObjDetectionScoreView
from utility.views import UtilityView,SwaggerUtilityView,SwaggerView,ImageGeneratorUtilityView,CodeUtilityView
from django.views.decorators.csrf import csrf_exempt


from rest_framework import permissions
from testUseCase.initLog import initiateLogging


initiateLogging()

create_lock()


pref='api/v1/'

urlpatterns=[
    path(pref+'downloadFile',csrf_exempt(UtilityView.as_view()), name="Download File"),
    path(pref+'pmml/zmk/convert',csrf_exempt(UtilityView.as_view()), name="Utility"),
    path(pref+'pmml/zmk/compile',csrf_exempt(ModelCompileView.as_view()), name="PMML"),
    path(pref+'models',csrf_exempt(ModelsView.as_view()), name="Models"),
    path(pref+'models/<modelName>',csrf_exempt(ModelOperationView.as_view()), name="Models"),
    path(pref+'models/<modelName>/score',csrf_exempt(ScoreView.as_view()), name="Models"),

    path(pref+'listOfLayers',NyokaServer.listOfLayers,name='listOfLayers'),
    path(pref+'pmml',csrf_exempt(PMMLView.as_view()), name="PMML"),
    path(pref+'pmml/<projectID>',csrf_exempt(PMMLOpeartionView.as_view()), name="PMML"),
    path(pref+'pmml/getGlobal/memory',csrf_exempt(PMMLGlobalView.as_view()), name="PMML"),
    path(pref+'pmml/<projectID>/layer',csrf_exempt(PMMLLayerView.as_view()), name="PMML"),

    path(pref+'runningTasks',csrf_exempt(RunningTaskView.as_view()), name="Running Tasks"),
    path(pref+'runningTasks/<id_for_task>',csrf_exempt(RunningTaskOperationView.as_view()), name="Running Tasks"),
    path(pref+'trainAutoMLModel',csrf_exempt(TrainAutoMLView.as_view()), name="Train Model"),
    path(pref+'trainNNModel',csrf_exempt(TrainNNView.as_view()), name="Train Model"),
    path(pref+'objectDetection/train/mrcnn',csrf_exempt(MRCNNView.as_view()), name="Train MRCNN"),
    path(pref+'code',csrf_exempt(CodeUtilityView.as_view()), name="Code Utility"),
    path(pref+'swagger',csrf_exempt(SwaggerView.as_view()), name='swagger'),
    path(pref,csrf_exempt(SwaggerView.as_view()),name='swagger'),
    path('',csrf_exempt(SwaggerView.as_view()),name='swagger'),
    path('swagger/v1/swagger.json',csrf_exempt(SwaggerUtilityView.as_view()),name='swagger')
]

