from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings

from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
# from rest_framework.decorators import api_view,renderer_classes,
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view,schema
import pandas as pd
import numpy as np
from sklearn.externals import joblib

from django.utils.encoding import smart_str
import os,ast, signal,operator,requests, json,time,datetime
from string import ascii_uppercase
from random import choice
from multiprocessing import Process, Lock

global DATA_MEMORY_OBJS_SKLEARN
import ast,pathlib
# RUNNING_TASK_MEMORY=[]
from utility.utilityClass import RUNNING_TASK_MEMORY
DATA_MEMORY_OBJS_SKLEARN={}
from trainModel import kerasUtilities,mergeTrainingNN,autoMLutilities,trainAutoMLV2,trainMaskRCNN

kerasUtilities = kerasUtilities.KerasUtilities()
autoMLutilities = autoMLutilities.AutoMLUtilities()

# from SwaggerSchema.schemas import (autoMLsendDataSwagger,
# 									autoMLtrainModelSwagger,
# 									statusOfModelSwagger,
# 									trainNeuralNetworkModelsSwagger,
# 									)


settingFilePath='settingFiles/'
pathOfStatus='resultStatus/'
SavedModels='SavedModels/'
logFolder='logs/'
runPorts=range(6006,6026)
runPortsUsage='inactive'
tensorboardPort=pd.DataFrame(data={'runPorts':runPorts,'runPortsUsage':runPortsUsage,'usedForLogs':None})
tensorboardPort.to_csv(settingFilePath+'tensorboardPort.txt',index=False)


runPorts=range(8888,8891)
runPortsUsage='inactive'
jupyterNotebook=pd.DataFrame(data={'runPorts':runPorts,'runPortsUsage':runPortsUsage,'usedForLogs':None})
jupyterNotebook.to_csv(settingFilePath+'jupyterNotebook.txt',index=False)


class Training:

	# @csrf_exempt
	# @api_view(['POST'])
	# @schema(trainNeuralNetworkModelsSwagger)
	# @api_view()
	def trainNeuralNetworkModels(userInput):
		# userInput=requests.body
		# userInput=json.loads(userInput)
		# print (userInput)
		pmmlFile=userInput['filePath']
		try:
			dataFolder=userInput['dataFolder']
		except:
			dataFolder='./logs/'+''.join(choice(ascii_uppercase) for i in range(12))+'/'
			kerasUtilities.checkCreatePath(dataFolder)

		try:
			fileName=userInput['filePath']
		except:
			fileName=userInput['filePath']
		try:
			tensorboardLogFolder=userInput['tensorboardLogFolder']
			print ('Log folder came correct')
		except:
			print ('Log folder has some issue')
			tensorboardLogFolder=target_path='./logs/'+''.join(choice(ascii_uppercase) for i in range(12))+'/'
			# print ('tensorboardLogFolder',tensorboardLogFolder)
			kerasUtilities.checkCreatePath(tensorboardLogFolder)
		
		lossType=userInput['loss']
		listOfMetrics=userInput['metrics']
		batchSize=userInput['batchSize']
		epoch=userInput['epoch']
		stepsPerEpoch=userInput['stepPerEpoch']
		problemType=userInput['problemType']
		testSize=userInput['testSize']
		scriptOutput=userInput['scriptOutput']
		optimizerName=userInput['optimizer']
		learningRate=userInput['learningRate']
		try:
			tensorboardUrl=userInput['tensorboardUrl']
		except:
			tensorboardUrl=''
		# idforData=pmmlFile.split('/')[-1].replace('.pmml','')
		idforData=os.path.basename(pmmlFile).replace('.pmml','')

		saveStatus=logFolder+idforData+'/'
		kerasUtilities.checkCreatePath(saveStatus)
		statusfileLocation=saveStatus+'status.txt'

		# print("status file generated")

		data_details={}
		data_details['pmmlFile']=idforData
		data_details['dataFolder']=dataFolder
		data_details['fileName']=fileName
		data_details['tensorboardLogFolder']=tensorboardLogFolder
		data_details['tensorboardUrl']=tensorboardUrl
		data_details['lossType']=lossType
		data_details['listOfMetrics']=listOfMetrics
		data_details['batchSize']=batchSize
		data_details['epoch']=epoch
		data_details['stepsPerEpoch']=stepsPerEpoch
		data_details['problemType']=problemType
		data_details['testSize']=testSize
		data_details['scriptOutput']=scriptOutput
		data_details['optimizerName']=optimizerName
		data_details['learningRate']=learningRate
		data_details['idforData']=idforData
		data_details['status']='In Progress'
		fObjScrpt=pathlib.Path(fileName)
		data_details['taskName']=fObjScrpt.name

		with open(statusfileLocation,'w') as filetosave:
			json.dump(data_details, filetosave)
		nntrainer = mergeTrainingNN.NeuralNetworkModelTrainer()

		pID = nntrainer.train(pmmlFile,dataFolder,fileName,tensorboardLogFolder,lossType,listOfMetrics,batchSize,\
			epoch,stepsPerEpoch,idforData,testSize,problemType,scriptOutput,optimizerName,learningRate)
		
		data_details['pID']=str(pID)
		saveStatus=logFolder+idforData+'/'
		kerasUtilities.checkCreatePath(saveStatus)
		statusfileLocation=saveStatus+'status.txt'

		if pID == -1:
			kerasUtilities.updateStatusOfTraining(statusfileLocation,'Training Failed')
		else:
			with open(statusfileLocation,'w') as filetosave:
				json.dump(data_details, filetosave)
		

		runTemp=[i['idforData'] for i in RUNNING_TASK_MEMORY]
		if data_details['idforData'] not in runTemp:
			# print ('PPPPPPPPPPPPPPPPPPPP Saved to runningTask')
			tempRunMemory={'idforData': idforData,
			'status': 'Training Failed' if pID==-1 else 'In Progress',
			'createdOn': str(datetime.datetime.now()),
			'type': 'NNProject',
			'pid':pID,
			'newPMMLFileName':fileName.split('/')[-1]}
			tempRunMemory['taskName']=data_details['taskName']
			RUNNING_TASK_MEMORY.append(tempRunMemory)
		else:
			pass

		return JsonResponse(data_details,status=202)


	# @csrf_exempt
	# @api_view(['POST'])
	# @schema(autoMLsendDataSwagger)
	def autoMLdataprocess(pathOffile):

		global DATA_MEMORY_OBJS_SKLEARN
		# pathOffile=requests.GET['filePath']
		data=pd.read_csv(pathOffile,encoding='latin-1')
		idforData=int(time.time())
		idforData=str(idforData)+'_autoML'
		DATA_MEMORY_OBJS_SKLEARN[idforData]=data

		# print(data.shape)
		data_details=autoMLutilities.dataDescription(data)
		data_details['idforData']=idforData
		return JsonResponse(data_details)


	# @csrf_exempt
	# @api_view(['POST'])
	# @schema(autoMLtrainModelSwagger)
	def autoMLtrainModel(userInput):
		global DATA_MEMORY_OBJS_SKLEARN	
		# userInput=requests.body
		# userInput=json.loads(userInput)
		paramToTrainModel=userInput['data']
		idforData=userInput['idforData']
		data=DATA_MEMORY_OBJS_SKLEARN[idforData]
		dataPath=userInput['filePath']
		targetVar=userInput['target_variable']
		problem_type=userInput['problem_type']
		# algorithms=userInput['parameters']['algorithm']
		try:
			algorithms=userInput['parameters']['algorithm']
			if algorithms[0]=='All':
				raise Exception("")
		except:
			if problem_type =='Regression':
				algorithms=['ExtraTreeRegressor','GradientBoostingRegressor','DecisionTreeRegressor','LinearSVR',\
        'RandomForestRegressor','XGBRegressor','KNeighborsRegressor','LinearRegression']
			else:
				algorithms=['DecisionTreeClassifier','ExtraTreesClassifier','RandomForestClassifier','GradientBoostingClassifier',\
        'KNeighborsClassifier','LinearSVC','LogisticRegression','XGBClassifier']
		try:
			newPMMLFileName = userInput['newPMMLFileName']
			if not newPMMLFileName.endswith('.pmml'):
				newPMMLFileName = newPMMLFileName+'.pmml'
		except:
			newPMMLFileName=idforData+'.pmml'


		projectName=idforData
		projectPath=logFolder+projectName
		dataFolder=projectPath+'/dataFolder/'
		tpotFolder=projectPath+'/tpotFolder/'

		try:
		    os.makedirs(projectPath)
		    os.mkdir(dataFolder)
		    os.mkdir(tpotFolder)
		except Exception as e:
		    print('>>>>>>>>>>>>>>>>', str(e))


		
		autoMLLock=Lock()
		trainer = trainAutoMLV2.AutoMLTrainer(algorithms=algorithms, problemType=problem_type)
		train_prc = Process(target=trainer.trainModel,args=(data,logFolder, newPMMLFileName, autoMLLock, userInput))
		# train_prc = Process(target=trainAutoMLV2.mainTrainAutoML,args=(data,paramToTrainModel,targetVar,idforData,problem_type,logFolder,newPMMLFileName))
		train_prc.start()
		pID=train_prc.ident
	 	
		statusFile=dataFolder+'status'+'.txt'
		# sFileText=sFile.read()
		# data_details=json.loads(sFileText)
		data_details={}
		data_details['pID']=str(pID)
		data_details['status']='In Progress'
		data_details['newPMMLFileName']=newPMMLFileName
		data_details['targetVar']=targetVar
		data_details['problem_type']=problem_type
		data_details['idforData']=idforData
		data_details['shape']=data.shape
		data_details['taskName']=newPMMLFileName.split('/')[-1]
		
		autoMLLock.acquire()
		with open(statusFile,'w') as filetosave:
		    json.dump(data_details, filetosave)
		autoMLLock.release()

		tempRunMemory={'idforData': projectName,
		      'status': 'In Progress',
		      'type': 'AutoMLProject',
		      'pid': pID,
		      'createdOn': str(datetime.datetime.now()),
		      'newPMMLFileName': newPMMLFileName.split('/')[-1]}
		tempRunMemory['taskName']=tempRunMemory['newPMMLFileName']
		print ('>>>>>>>>>>>>>>>>>>>>AutoML',tempRunMemory)

		RUNNING_TASK_MEMORY.append(tempRunMemory)

		# print ('RUNNING_TASK_MEMORY >>>>>>>>>',RUNNING_TASK_MEMORY)

		return JsonResponse(data_details,status=202)


	
	def statusOfModel(idforData):
		try:
			projectName=idforData
			# print ('STep 1')
			data_details=autoMLutilities.readStatusFile(projectName)
			# print ('STep 2')
			data_details['generationInfo']=autoMLutilities.progressOfModel(logFolder,projectName)
			# print ('STep 3')
		except:
			projectName=idforData
			# print ('STep 1')
			data_details=autoMLutilities.readStatusFile(projectName)
			# print ('STep 2')

		# print ('MMMMMMMMMMMM',data_details)
		# for j in data_details:
		# 	print (j,type(data_details[j]))
		return JsonResponse(data_details,status=200)


	def trainMRCNN(userInput):
		# userInput=requests.body
		# userInput=json.loads(userInput)
		# print (userInput)
		pmmlFile=userInput['filePath']
		try:
			dataFolder=userInput['dataFolder']
		except:
			print ('Get Data folder')

		try:
			tensorboardLogFolder=userInput['tensorboardLogFolder']
		except:
			tensorboardLogFolder=target_path='./logs/'+''.join(choice(ascii_uppercase) for i in range(12))+'/'
			# print ('tensorboardLogFolder',tensorboardLogFolder)
			kerasUtilities.checkCreatePath(tensorboardLogFolder)
		
		# batchSize=userInput['batchSize']
		epoch=userInput['epoch']
		stepsPerEpoch=userInput['stepPerEpoch']
		# learningRate=userInput['learningRate']
		try:
			tensorboardUrl=userInput['tensorboardUrl']
		except:
			tensorboardUrl=''
		# idforData=pmmlFile.split('/')[-1].replace('.pmml','')
		idforData=os.path.basename(pmmlFile).replace('.pmml','')+'_MRCNN'

		saveStatus=logFolder+idforData+'/'
		kerasUtilities.checkCreatePath(saveStatus)
		statusfileLocation=saveStatus+'status.txt'

		# print("status file generated")

		data_details={}
		data_details['pmmlFile']=idforData
		data_details['dataFolder']=dataFolder
		data_details['fileName']=pmmlFile
		data_details['tensorboardLogFolder']=tensorboardLogFolder
		data_details['tensorboardUrl']=tensorboardUrl
		# data_details['batchSize']=batchSize
		data_details['epoch']=epoch
		data_details['stepsPerEpoch']=stepsPerEpoch
		# data_details['learningRate']=learningRate
		data_details['idforData']=idforData
		data_details['status']='Building Architecture'

		with open(statusfileLocation,'w') as filetosave:
			json.dump(data_details, filetosave)
		
		objtrainer = trainMaskRCNN.ObjectDetetctionModels()

		prc = Process(target=objtrainer.train, args=(pmmlFile,dataFolder,statusfileLocation,idforData,epoch,\
			tensorboardLogFolder,stepsPerEpoch))
		prc.start()
		pID = prc.ident
		
		data_details['pID']=str(pID)


		if pID == -1:
			kerasUtilities.updateStatusOfTraining(statusfileLocation,'Training Failed')
		else:
			with open(statusfileLocation,'w') as filetosave:
				json.dump(data_details, filetosave)
		

		runTemp=[i['idforData'] for i in RUNNING_TASK_MEMORY]
		if data_details['idforData'] not in runTemp:
			# print ('PPPPPPPPPPPPPPPPPPPP Saved to runningTask')
			tempRunMemory={'idforData': idforData,
			'status': 'Training Failed' if pID==-1 else 'In Progress',
			'createdOn': str(datetime.datetime.now()),
			'type': 'ObjectDetectionProject',
			'pid':pID,
			'newPMMLFileName':idforData+'.pmml'}
			tempRunMemory['taskName']=tempRunMemory['newPMMLFileName']
			RUNNING_TASK_MEMORY.append(tempRunMemory)
		else:
			pass

		return JsonResponse(data_details,status=202)