import torch
import torch.nn as nn
import torchvision.models as models

import common


class resnet(nn.Module):
    def __init__(self):
        super(resnet).__init__()
        self.model=models.resnet50(pretrained=False)
        self.model=nn.Conv2d
        self.model.fc=nn.Linear(in_features=4096,out_features=common.captcha_size*common.captcha_array.__len__())
        print(self.model)

    def forward(self, x):
        x=self.model(x)
        return x

if __name__ == '__main__':
    m=resnet()
    x=torch.randn(1,1,60,160)
    y=m(x)