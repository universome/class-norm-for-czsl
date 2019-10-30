from typing import Tuple

import numpy as np
import torch
import torch.nn as nn
from torch import Tensor
from firelab.config import Config


class FeatGenerator(nn.Module):
    def __init__(self, config: Config):
        super(FeatGenerator, self).__init__()

        self.config = config
        self.attr_emb = nn.Linear(config.attr_input_dim, config.attr_output_dim)
        self.model = nn.Sequential(
            nn.Linear(config.z_dim + config.attr_output_dim, config.hid_dim),
            nn.LeakyReLU(),
            nn.Linear(config.hid_dim, config.feat_dim),
        )

    def forward(self, z: Tensor, attr: Tensor) -> Tensor:
        assert z.size(0) == attr.size(0), "You should specify necessary attr for each z yourself"

        attr_feats = self.attr_emb(attr)
        x = torch.cat([z, attr_feats], dim=1)
        x = self.model(x)

        return x

    def sample_noise(self, batch_size: int) -> Tensor:
        return torch.randn(batch_size, self.config.z_dim)


class FeatDiscriminator(nn.Module):
    def __init__(self, config: Config, attrs: np.ndarray=None):
        super(FeatDiscriminator, self).__init__()

        self.config = config
        self.body = nn.Sequential(
            nn.Linear(config.feat_dim, config.hid_dim),
            nn.ReLU()
        )
        self.discr_head = nn.Linear(config.hid_dim, 1)
        self.cls_head = nn.Linear(config.hid_dim, config.num_classes)

        if config.get('use_attrs_in_discr'):
            assert not attrs is None, "You should provide attrs to use attrs"

            self.register_buffer('attrs', attrs)
            self.cls_attr_emb = nn.Linear(config.attr_input_dim, config.hid_dim)
            self.biases = nn.Parameter(torch.zeros(attrs.shape[0]))

    def forward(self, x: Tensor) -> Tuple[Tensor, Tensor]:
        feats = self.body(x)
        discr_logits = self.discr_head(feats)
        cls_logits = self.compute_cls_logits_with_attrs(feats)

        return discr_logits, cls_logits

    def run_discr_head(self, x: Tensor) -> Tensor:
        return self.discr_head(self.body(x))

    def run_cls_head(self, x: Tensor) -> Tensor:
        return self.compute_cls_logits_with_attrs(self.body(x))

    def compute_cls_logits_with_attrs(self, x_feats: Tensor) -> Tensor:
        if self.config.get('use_attrs_in_discr'):
            attr_embs = self.cls_attr_emb(self.attrs)
            logits = torch.mm(x_feats, attr_embs.t()) + self.biases
        else:
            logits = self.cls_head(x_feats)

        return logits
