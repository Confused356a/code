import shutil, os
if os.path.exists("logs"):
    shutil.rmtree("logs")
os.makedirs("logs", exist_ok=True)

import torch
from torch import nn
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter

import my_datasets
from model import mymodel

if __name__ == '__main__':
    train_datas=my_datasets.mydatasets("./dataset/train")
    test_data=my_datasets.mydatasets("./dataset/test")
    train_dataloader=DataLoader(train_datas,batch_size=64,shuffle=True)
    test_dataloader = DataLoader(test_data, batch_size=64, shuffle=True)
    writer=SummaryWriter("logs")
    m=mymodel().cuda()

    loss_fn=nn.MultiLabelSoftMarginLoss().cuda() #多标签交叉熵损失函数（每个验证码有四个）
    optimizer = torch.optim.Adam(m.parameters(), lr=0.001) #优化器选择Adam，学习率0.001
    #一般要求学习率比较小
    w=SummaryWriter("logs")
    total_step=0

for i in range(50):
    for i,(imgs,targets) in enumerate(train_dataloader):
        imgs=imgs.cuda()
        targets=targets.cuda()
        # print(imgs.shape)
        # print(targets.shape)
        outputs=m(imgs)
        # print(outputs.shape)
        loss = loss_fn(outputs, targets)
        optimizer.zero_grad()

        loss.backward()
        optimizer.step()

        if i%10==0:
            total_step+=1
            print("训练{}次,loss:{}".format(total_step*10, loss.item()))
            w.add_scalar("loss",loss,total_step)

        # writer.add_images("imgs", imgs, i)
    writer.close()

torch.save(m,"model.pth") #保存模型


