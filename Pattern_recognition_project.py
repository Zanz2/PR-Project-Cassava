
# coding: utf-8

# First check that you have pytorch installed, instructions are here: https://pytorch.org/get-started/locally/ , prefferably do it with anaconda if you can, I think that will lead to less problems down the road if we use other libraries.
# 
# If cuda toolkit isnt available and you have an nvidia gpu try to get that too (it might be contained within anaconda pytorch package): https://docs.nvidia.com/cuda/cuda-installation-guide-microsoft-windows/index.html
# 
# Also note that because the dataset is large I added it to the .gitignore, you should download it from here : https://www.kaggle.com/c/cassava-leaf-disease-classification/data, and extract it into the data/ folder of the project
# 

# In[1]:


import torch
import os 
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as img
import torchvision
import pandas as pd
import skorch


from torch import FloatTensor, LongTensor, nn, optim
from torch.utils.data import Dataset, DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from torchvision import transforms, datasets, models
from IPython.core.debugger import set_trace

get_ipython().run_line_magic('matplotlib', 'inline')

use_cuda = True
if not torch.cuda.is_available() or not use_cuda:
    print("if you have an nvidia gpu get the cuda core package")
    device = torch.device('cpu')
else:
    print("cuda is available")
    device = torch.device('cuda:0')


# Splitting data into train and test sets and loading the validation set

# In[2]:


#setting the path to the directory containing the pics
path = './data/train_images'
test_path = './data/test_images'

labelled_dataset = pd.read_csv(r'./data/train.csv')
submission = pd.read_csv(r'./data/sample_submission.csv')

with open('./data/label_num_to_disease_map.json') as f:
    mapping_dict = json.load(f)
print(mapping_dict)

train, test = train_test_split(labelled_dataset, test_size=0.25, random_state=7, stratify=labelled_dataset.label)

should_match_index = 1
print(labelled_dataset.values[should_match_index])


# In[3]:


from collections import Counter

Counter(labelled_dataset.label) # counts the elements' frequency


# Label Cassava Bacterial Blight (CBB) appears 1087 times<br>
# Label Cassava Brown Streak Disease (CBSD) appears 2189 times<br>
# Label Cassava Green Mottle (CGM) appears 2386 times<br>
# Label Cassava Mosaic Disease (CMD) appears 13158 times<br>
# Label Healthy appears 2577 times<br>
# Because the labels arent equally represented the dataset split is stratified so each split has an equal amount of a certain label
# <br><br>
# Create custom dataset class for the images, and a transform to be applied to these images as part of preprocessing for learning <br>
# All pre-trained models expect input images normalized in the same way, i.e. mini-batches of 3-channel RGB images of shape (3 x H x W), where H and W are expected to be at least 224. The images have to be loaded in to a range of [0, 1] and then normalized using mean = [0.485, 0.456, 0.406] and std = [0.229, 0.224, 0.225].
# 

# In[4]:



class CassavaDataset(Dataset):
    def __init__(self, data, path , transform = None):
        super().__init__()
        self.data = data.values
        self.path = path
        self.transform = transform
        
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self,index):
        img_name,label = self.data[index]
        img_path = os.path.join(self.path, img_name)
        image = img.imread(img_path)
        if self.transform is not None:
            image = self.transform(image)
        return image, label

# original resolution is 800 x 600

cassava_transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((600,600)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomResizedCrop(299), #299 for inceptionv3 224 for everything else
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]) # This should be calculated, instead of hard coded 
    # (the means and standard deviations of each of the 3 image channels)
])

train_dataset = CassavaDataset(train, path, cassava_transform )
test_dataset = CassavaDataset(test, path, cassava_transform)
valid_dataset = CassavaDataset(submission, test_path, cassava_transform)

print(len(train_dataset))
print(len(test_dataset))
print(len(valid_dataset))
print(len(labelled_dataset))


# In[5]:


train_dataset[0] # how an image looks with 3 normalized channel, its label is 2


# In[6]:


n_epochs = 10
num_classes = 5
batch_size = 16
learning_rate = 0.03

train_dataloader = DataLoader(dataset = train_dataset, batch_size = batch_size, shuffle=True, num_workers=0,pin_memory=True)
valid_dataloader = DataLoader(dataset = valid_dataset, batch_size = batch_size, shuffle=False, num_workers=0,pin_memory=True)
test_dataloader = DataLoader(dataset = test_dataset, batch_size = batch_size, shuffle=False, num_workers=0,pin_memory=True)


# Show an image from the dataset

# In[7]:


def show_image(index):  
    plt.imshow(img.imread('{}/{}'.format(path,labelled_dataset.values[index][0]))) # set the correct resolution here
    print('Index: {}'.format(labelled_dataset.values[index][1]))
    print('Filename: {}'.format(labelled_dataset.values[index][0]))
    
show_image(6)


# Using resnet 18 pretrained pytorch model

# In[8]:


print("PyTorch Version: ",torch.__version__)
print("Torchvision Version: ",torchvision.__version__) 
# Use this number below as the torchvision version or else theres a version conflict


# Model selection below, choices are "resnet", "alexnet", "vgg", "google"

# In[ ]:



model_string = "google"

if model_string == "google":
    net = models.inception_v3(pretrained=True) # googlenet is based on inception v1, this is improved
    net = net.cuda() if device else net
    num_ftrs = net.fc.in_features
    net.fc = nn.Linear(num_ftrs, num_classes)
    net.fc = net.fc.cuda() if use_cuda else net.fc
    
    
if model_string == "vgg":
    net = models.vgg16(pretrained=True)
    net = net.cuda() if device else net
    net.fc = nn.Linear(100, num_classes)
    net.fc = net.fc.cuda() if use_cuda else net.fc
    
    
if model_string == "alexnet":
    net = models.alexnet(pretrained=True)
    net = net.cuda() if device else net  
    net.fc = nn.Linear(100, num_classes)
    net.fc = net.fc.cuda() if use_cuda else net.fc
    

if model_string == "resnet":
    #net = torch.hub.load('pytorch/vision:v0.2.2', 'resnet18', pretrained=True)
    net = models.resnet18(pretrained=True)
    net = net.cuda() if device else net
    num_ftrs = net.fc.in_features
    net.fc = nn.Linear(num_ftrs, num_classes)
    net.fc = net.fc.cuda() if use_cuda else net.fc
    
def accuracy(out, labels):
    _,pred = torch.max(out, dim=1)
    return torch.sum(pred==labels).item()

criterion = nn.CrossEntropyLoss()
#optimizer = optim.SGD(net.parameters(), lr=learning_rate, momentum=0.9)
optimizer = optim.Adam(net.parameters(), lr=learning_rate)


# Do evaluation, (still have to try out parameters specified in paper, find out which are useful) <br>The original base code for the block above this text and the 2 blocks below was found at the following link, but it was modified for our dataset and to work with our 4 different models not just resnet: https://www.pluralsight.com/guides/introduction-to-resnet

# In[ ]:


print_every = int(len(train_dataloader)*0.1) # print upon completion of every 10% of the dataset
valid_loss_min = np.Inf
val_loss = []
val_acc = []
train_loss = []
train_acc = []
total_step = len(train_dataloader)
for epoch in range(1, n_epochs+1):
    running_loss = 0.0
    correct = 0
    total=0
    print(f'Epoch {epoch}\n')
    for batch_idx, (data_, target_) in enumerate(train_dataloader):
        data_, target_ = data_.to(device), target_.to(device)
        optimizer.zero_grad()
        
        outputs = net(data_)
        if len(outputs)>1:
            outputs = outputs[0]
        loss = criterion(outputs, target_)
        loss.backward()
        optimizer.step()

        running_loss += loss.item()
        _,pred = torch.max(outputs, dim=1)
        
        #set_trace() # Debugger entrypoint for inspecting predictions
        
        correct += torch.sum(pred==target_).item()
        total += target_.size(0)
        if (batch_idx) % print_every == 0:
            print ('Epoch [{}/{}], Step [{}/{}], Loss: {:.4f}' 
                   .format(epoch, n_epochs, batch_idx, total_step, loss.item()))
    train_acc.append(100 * correct / total)
    train_loss.append(running_loss/total_step)
    print(f'\ntrain-loss: {np.mean(train_loss):.4f}, train-acc: {(100 * correct/total):.4f}')
    batch_loss = 0
    total_t=0
    correct_t=0
    with torch.no_grad():
        net.eval()
        for data_t, target_t in (test_dataloader):
            data_t, target_t = data_t.to(device), target_t.to(device)
            outputs_t = net(data_t)
            if len(outputs_t)>1:
                outputs_t = outputs_t[0]
            loss_t = criterion(outputs_t, target_t)
            batch_loss += loss_t.item()
            _,pred_t = torch.max(outputs_t, dim=1)
            correct_t += torch.sum(pred_t==target_t).item()
            total_t += target_t.size(0)
        val_acc.append(100 * correct_t/total_t)
        val_loss.append(batch_loss/len(test_dataloader))
        network_learned = batch_loss < valid_loss_min
        print(f'validation loss: {np.mean(val_loss):.4f}, validation acc: {(100 * correct_t/total_t):.4f}\n')

        
        if network_learned:
            valid_loss_min = batch_loss
            torch.save(net.state_dict(), './data/current_best_resnet18.pt')
            print('Improvement-Detected, save-model')
    net.train()
#print(target_,pred)


# With 5 epochs and batch size 4 it took around 25 mins on my machine, with cuda cores

# In[ ]:


fig = plt.figure(figsize=(20,10))
plt.title("Train-Validation Accuracy")
plt.plot(train_acc, label='train')
plt.plot(val_acc, label='validation')
plt.xlabel('num_epochs', fontsize=12)
plt.ylabel('accuracy', fontsize=12)
plt.legend(loc='best')


# In[ ]:


#del train_dataloader
#del test_dataloader
#torch.cuda.empty_cache()
