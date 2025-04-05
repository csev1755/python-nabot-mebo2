import torch
import torchvision.transforms as transforms
from torchvision import models
from torchvision.models import ResNet18_Weights, AlexNet_Weights, VGG16_Weights, \
    DenseNet161_Weights, Inception_V3_Weights, MobileNet_V2_Weights, \
    Wide_ResNet50_2_Weights, ResNeXt50_32X4D_Weights, GoogLeNet_Weights 
import logging
import numpy as np
from PIL import Image
import random
import time

class FeatureExtractor():
    def __init__(self, model_name='resnet'):
        if model_name == 'resnet':
            self.model = models.resnet18(weights=ResNet18_Weights.DEFAULT)
        elif model_name == 'alexnet':
            self.model = models.alexnet(weights=AlexNet_Weights.DEFAULT)
        elif model_name == 'vgg16':
            self.model = models.vgg16(weights=VGG16_Weights.DEFAULT)
        elif model_name == 'densenet':
            self.model = models.densenet161(weights=DenseNet161_Weights.DEFAULT)
        elif model_name == 'inception':
            self.model = models.inception_v3(weights=Inception_V3_Weights.DEFAULT)
        elif model_name == 'googlenet':
            self.model = models.googlenet(weights=GoogLeNet_Weights.DEFAULT)
        elif model_name == 'mobilenet':
            self.model = models.mobilenet_v2(weights=MobileNet_V2_Weights.DEFAULT)
        elif model_name == 'resnext':
            self.model = models.resnext50_32x4d(weights=ResNeXt50_32X4D_Weights.DEFAULT)
        elif model_name == 'wide_resnet':
            self.model = models.wide_resnet50_2(weights=Wide_ResNet50_2_Weights.DEFAULT)

        if torch.cuda.is_available():
            self.model.cuda()

        self.model.eval()

        normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225])
        
        self.input_transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            normalize,
        ])

    def get_features(self, images):
        input_image = self.normalize_input(images)

        if input_image.ndim == 3:
            input_image = input_image[np.newaxis]

        if torch.cuda.is_available():
            input_image = input_image.cuda()
        # compute output
        start = time.time()
        with torch.no_grad():
            pred = self.model(input_image)
        # torch.cuda.synchronize()
        gpu_time = time.time() - start
        logging.info("classifier: time spent on gpu {}".format(gpu_time))
        return pred.cpu()

    def normalize_input(self, input_image):
        return self.input_transform(input_image)



if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s  %(name)s  %(levelname)s: %(message)s', level=logging.INFO)
    input_img = Image.new('RGB',(224,224))
    pixels = input_img.load()
    for x in range(input_img.size[0]):
        for y in range(input_img.size[1]):
            pixels[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

    FE = FeatureExtractor(model_name='mobilenet')
    
    features = FE.get_features(input_img)
    print(features.size())