# import dependencies
import os
from data import preprocess_data, load_training_validation_data, load_test_data
from dnn import Net1, Net2
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.transforms as transforms
import PIL
import random
import numpy as np

# preprocess data
if not os.path.isdir('validation_set'):
	preprocess_data()

# load data
data = load_training_validation_data()

# training data
training_set = data[0]
original_training_loader = training_set['original']
imadjust_training_loader = training_set['imadjust']
histeq_training_loader = training_set['histeq']
adapthisteq_training_loader = training_set['adapthisteq']

# validation data
validation_set = data[1]
original_validation_loader = validation_set['original']
imadjust_validation_loader = validation_set['imadjust']
histeq_validation_loader = validation_set['histeq']
adapthisteq_validation_loader = validation_set['adapthisteq']

# test data
test_loader = load_test_data()

# instantiate DNNs
nets = {}
nets['original_net1'] = Net1()
nets['original_net2'] = Net2()

nets['imadjust_net1'] = Net1()
nets['imadjust_net2'] = Net2()

nets['histeq_net1'] = Net1()
nets['histeq_net2'] = Net2()

nets['adapthisteq_net1'] = Net1()
nets['adapthisteq_net2'] = Net2()

# setup device
device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
print(device)

# train DNNs
print('training DNNs')
for net_name in nets.keys():
	net = nets[net_name]
	net.to(device)

	if 'original' in net_name:
		training_loader = original_training_loader
		validation_loader = original_validation_loader
	elif 'imadjust' in net_name:
		training_loader = imadjust_training_loader
		validation_loader = imadjust_validation_loader
	elif 'histeq' in net_name:
		training_loader = histeq_training_loader
		validation_loader = histeq_validation_loader
	else:
		training_loader = adapthisteq_training_loader
		validation_loader = adapthisteq_validation_loader

    # define loss function and optimizer
	criterion = nn.CrossEntropyLoss()
	optimizer = optim.Adam(net.parameters())
    
	# train net
	print('training', net_name)
	
	for epoch in range(50):
		for _, data in enumerate(training_loader):
			inputs = data[0]
			labels = data[1]

			# apply perturbations
			for i in range(len(inputs)):
				perturbation = random.choice([0, 1, 2, 3])
				if perturbation == 1:
					image = transforms.ToPILImage()(inputs[i])
					image = transforms.RandomAffine(degrees = 0, translate = (0.1, 0.1), resample = PIL.Image.BILINEAR)(image)
					inputs[i] = transforms.ToTensor()(image)
				elif perturbation == 2:
					image = transforms.ToPILImage()(inputs[i])
					image = transforms.RandomResizedCrop(size = 48, ratio = (1, 1))(image)
					inputs[i] = transforms.ToTensor()(image)
				elif perturbation == 3:
					image = transforms.ToPILImage()(inputs[i])
					image = transforms.RandomRotation(degrees = 5, resample = PIL.Image.BILINEAR)(image)
					inputs[i] = transforms.ToTensor()(image)
				else:
					continue

			inputs = inputs.to(device)
			labels = labels.to(device)

			# optimize
			optimizer.zero_grad()

			outputs = net(inputs)
			loss = criterion(outputs, labels)
			loss.backward()
			optimizer.step()
			
		# print current loss
		print('epoch:', epoch + 1)
		print('training loss:', loss.item())

		# check validation loss
		net.to('cpu')
		validation_inputs, validation_labels = next(iter(validation_loader))
		validation_loss = criterion(net(validation_inputs), validation_labels)
		net.to(device)

		print('validation loss:', validation_loss.item())

		if validation_loss == 0:
			break

# create MCDNN
# pass test data through DNNs
dnn_outputs = []
for net in nets.values():
	dnn_outputs.append(net(test_loader))

# average results
mcdnn_output = dnn_outputs[0]
for dnn_output in dnn_outputs[1:]:
	mcdnn_output.add_(dnn_output)

mcdnn_output.div_(len(dnn_outputs))

# compute predictions
_, predictions = torch.argmax(mcdnn_output, dim = 0)

# save data
file_out = open('test_out.csv', 'w+')
np.savetxt(file_out, predictions.numpy(), delimiter = ',')
file_out.close()