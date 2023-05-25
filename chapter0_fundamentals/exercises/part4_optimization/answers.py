# %%
import os; os.environ["ACCELERATE_DISABLE_RICH"] = "1"
import sys
import pandas as pd
import torch as t
from torch import optim
import torch.nn.functional as F
from torchvision import datasets
from torch.utils.data import DataLoader, Subset
from typing import Callable, Iterable, Tuple, Optional
import pytorch_lightning as pl
from pytorch_lightning.loggers import CSVLogger, WandbLogger
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from IPython.display import display, HTML

# Make sure exercises are in the path
chapter = r"chapter0_fundamentals"
exercises_dir = Path(f"{os.getcwd().split(chapter)[0]}/{chapter}/exercises").resolve()
section_dir = exercises_dir / "part4_optimization"
if str(exercises_dir) not in sys.path: sys.path.append(str(exercises_dir))
os.chdir(section_dir)

from plotly_utils import bar, imshow
from part3_resnets.solutions import IMAGENET_TRANSFORM, get_resnet_for_feature_extraction, plot_train_loss_and_test_accuracy_from_metrics
from part4_optimization.utils import plot_fn, plot_fn_with_points
import part4_optimization.tests as tests

device = t.device("cuda" if t.cuda.is_available() else "cpu")

MAIN = __name__ == "__main__"

# %%
def pathological_curve_loss(x: t.Tensor, y: t.Tensor):
    # Example of a pathological curvature. There are many more possible, feel free to experiment here!
    x_loss = t.tanh(x) ** 2 + 0.01 * t.abs(x)
    y_loss = t.sigmoid(y)
    return x_loss + y_loss


if MAIN:
    plot_fn(pathological_curve_loss)
# %%
def opt_fn_with_sgd(fn: Callable, xy: t.Tensor, lr=0.001, momentum=0.98, n_iters: int = 100):
    '''
    Optimize the a given function starting from the specified point.

    xy: shape (2,). The (x, y) starting point.
    n_iters: number of steps.
    lr, momentum: parameters passed to the torch.optim.SGD optimizer.

    Return: (n_iters, 2). The (x,y) BEFORE each step. So out[0] is the starting point.
    '''
    xy_history = [] 

    optimizer = t.optim.SGD([xy], lr=lr, momentum=momentum)
    for _ in range(n_iters):
        xy_history.append(xy.detach().clone())
        x, y = xy
        loss = fn(x, y)
        loss.backward()
        optimizer.step()
        optimizer.zero_grad()

    return t.stack(xy_history, dim=0)

# %%
if MAIN:
    points = []

    optimizer_list = [
        # (optim.SGD, {"lr": 0.1, "momentum": 0.0}),
        # (optim.SGD, {"lr": 0.02, "momentum": 0.99}),
        # (optim.SGD, {"lr": 0.1, "momentum": 0.90}),
        (optim.SGD, {"lr": 0.5, "momentum": 0.90}),
        # (optim.SGD, {"lr": 0.6, "momentum": 0.90}),
        # (optim.SGD, {"lr": 0.8, "momentum": 0.90}),
        (optim.SGD, {"lr": 1.0, "momentum": 0.90}),
        (optim.SGD, {"lr": 0.5, "momentum": 0.95}),
        (optim.SGD, {"lr": 1.0, "momentum": 0.95}),
        (optim.SGD, {"lr": 0.5, "momentum": 0.99}),
        (optim.SGD, {"lr": 1.0, "momentum": 0.99}),
    ]

    for optimizer_class, params in optimizer_list:
        xy = t.tensor([2.5, 2.5], requires_grad=True)
        xys = opt_fn_with_sgd(pathological_curve_loss, xy=xy, lr=params['lr'], momentum=params['momentum'], n_iters=100)

        points.append((xys, optimizer_class, params))

    plot_fn_with_points(pathological_curve_loss, points=points)
# %%
class SGD:
    def __init__(
        self, 
        params: Iterable[t.nn.parameter.Parameter], 
        lr: float, 
        momentum: float = 0.0, 
        weight_decay: float = 0.0
    ):
        '''Implements SGD with momentum.

        Like the PyTorch version, but assume nesterov=False, maximize=False, and dampening=0
            https://pytorch.org/docs/stable/generated/torch.optim.SGD.html#torch.optim.SGD

        '''
        self.params = list(params) # turn params into a list (because it might be a generator)
        self.lr = lr
        self.momentum = momentum
        self.weight_decay = weight_decay
        self.prev_g = [0] * len(self.params)
        

    def zero_grad(self) -> None:
        for param in self.params:
            param.grad = t.zeros_like(param)

    @t.inference_mode()
    def step(self) -> None:
        for i, (param, prev_g) in enumerate(zip(self.params, self.prev_g)):
            g = param.grad + self.weight_decay * param.data + self.momentum * prev_g
            param -= self.lr * g
            self.prev_g[i] = g.detach().clone()

    def __repr__(self) -> str:
        return f"SGD(lr={self.lr}, momentum={self.mu}, weight_decay={self.lmda})"



if MAIN:
    tests.test_sgd(SGD)
# %%
