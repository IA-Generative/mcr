from enum import StrEnum

import torch


class ComputeDevice(StrEnum):
    CPU = "cpu"
    GPU = "cuda"


def is_gpu_available() -> bool:
    return torch.cuda.is_available()


def get_gpu_name(index: int = 0) -> str:
    return torch.cuda.get_device_name(index)


def get_default_gpu_device() -> torch.device:
    return torch.device("cuda")
