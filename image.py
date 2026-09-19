import torch
from torchvision import transforms, models
from torchvision.models import ResNet18_Weights
from PIL import Image

weights = ResNet18_Weights.IMAGENET1K_V1
model = models.resnet18(weights=weights)
model.eval()

preprocess = weights.transforms()

img = Image.open(r"C:\Users\muham\Pictures\Images\corgi.jpg")
batch = preprocess(img).unsqueeze(0)
with torch.no_grad():
    output = model(batch)

probs = torch.nn.functional.softmax(output[0], dim=0)
class_id = probs.argmax().item()
class_name = weights.meta["categories"][class_id]
confidence = probs[class_id].item()

print(f"Prediction: {class_name} ({confidence*100:2f}%)")
