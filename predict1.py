import torch
from model import mymodel  # 导入你定义的模型类（和训练时一致）
from PIL import Image
import torchvision.transforms as transforms

# 1. 加载模型
model = mymodel()  # 实例化你的模型
model.load_state_dict(torch.load("model.pth"))  # 加载权重（若训练时用torch.save(model, ...)则直接model = torch.load("model.pth")）
model.eval()  # 设为评估模式
model.cuda() if torch.cuda.is_available() else model.cpu()

# 2. 定义图像预处理（和训练时一致）
transform = transforms.Compose([
    transforms.Resize((60, 160)),  # 改成你训练时的尺寸
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])  # 训练时的归一化参数
])


# 3. 测试单张验证码
def predict_captcha(image_path):
    img = Image.open(image_path).convert("RGB")  # 读取图片
    img_tensor = transform(img).unsqueeze(0)  # 增加batch维度
    img_tensor = img_tensor.cuda() if torch.cuda.is_available() else img_tensor.cpu()

    with torch.no_grad():  # 推理时关闭梯度
        outputs = model(img_tensor)
        # 假设你的模型输出是4个分类头（对应4位验证码），这里要和训练时的输出解析逻辑一致
        # 示例：若输出是4个(bs, num_classes)的张量，取每个的argmax
        captcha = ""
        for output in outputs:
            pred = torch.argmax(output, dim=1).item()
            # 把数字映射回字符（比如训练时用的字符表是"0123456789abcdef..."）
            char_map = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"  # 改成你训练时的字符表
            captcha += char_map[pred]
    return captcha


# 测试
if __name__ == "__main__":
    result = predict_captcha("dataset/test/0xdy_1769267106.png")  # 替换为你的测试图片路径
    print("识别结果：", result)