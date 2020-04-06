import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor
from firelab.config import Config

from src.utils.constants import NEG_INF


def validate_clf(clf_model: nn.Module, dataloader, device: str='cpu'):
    losses = []
    accs = []

    with torch.no_grad():
        for x, y in dataloader:
            x = torch.from_numpy(x).to(device)
            y = torch.tensor(y).to(device)

            logits = clf_model(x)
            loss = F.cross_entropy(logits, y, reduction='none').cpu().tolist()
            acc = compute_guessed(logits, y).tolist()

            losses.extend(loss)
            accs.extend(acc)

    return np.mean(losses), np.mean(accs)


def construct_optimizer(parameters, optim_config: Config):
    if optim_config.type == 'sgd':
        return torch.optim.SGD(parameters, **optim_config.kwargs)
    elif optim_config.type == 'adam':
        return torch.optim.Adam(parameters, **optim_config.kwargs)
    else:
        raise NotImplementedError(f'Unknown optimizer: {optim_config.type}')


def compute_accuracy(logits: Tensor, targets: Tensor, *args, **kwargs) -> Tensor:
    return compute_guessed(logits, targets, *args, **kwargs).mean()


def compute_guessed(logits: Tensor, targets: Tensor, to_device='cpu') -> Tensor:
    assert logits.ndim == 2
    assert targets.ndim == 1
    assert len(logits) == len(targets)

    return (logits.argmax(dim=1) == targets).float().detach().to(to_device)


def prune_logits(logits: Tensor, output_mask:np.ndarray) -> Tensor:
    """
    Takes logits and sets those classes which do not participate
    in the current task to -infinity so they are not explicitly penalized and forgotten
    """
    mask_idx = np.nonzero(~output_mask)[0]
    pruned = logits.index_fill(1, torch.tensor(mask_idx).to(logits.device), NEG_INF)

    return pruned


def normalize(data: Tensor, scale_value: float=1., detach: bool=True) -> Tensor:
    norms = data.norm(dim=-1, keepdim=True)
    norms = norms.detach() if detach else norms

    return scale_value * (data / norms)
