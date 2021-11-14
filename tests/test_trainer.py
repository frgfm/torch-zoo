from typing import Optional

import pytest
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision.models.detection import fasterrcnn_mobilenet_v3_large_320_fpn

from holocron import trainer
from holocron.trainer.core import Trainer
from holocron.nn import GlobalAvgPool2d


class MockClassificationDataset(Dataset):
    """Mock dataset generating a random sample and a fixed zero target"""
    def __init__(self, n):
        super().__init__()
        self.n = n

    def __getitem__(self, idx):
        return torch.rand((3, 32, 32)), 0

    def __len__(self):
        return self.n


class MockBinaryClassificationDataset(Dataset):
    """Mock dataset generating a random sample and a fixed zero probability"""
    def __init__(self, n):
        super().__init__()
        self.n = n

    def __getitem__(self, idx):
        return torch.rand((3, 32, 32)), torch.zeros((1,))

    def __len__(self):
        return self.n


class MockSegDataset(Dataset):
    """Mock dataset generating a random sample and a fixed zero target"""
    def __init__(self, n):
        super().__init__()
        self.n = n

    def __getitem__(self, idx):
        return torch.rand((3, 32, 32)), torch.zeros((32, 32), dtype=torch.long)

    def __len__(self):
        return self.n


class MockDetDataset(Dataset):
    """Mock dataset generating a random sample and a fixed zero target"""
    def __init__(self, n):
        super().__init__()
        self.n = n

    def __getitem__(self, idx):
        boxes = torch.tensor([[0, 0, 1, 1], [0.25, 0.25, 0.75, 0.75]], dtype=torch.float32)
        return torch.rand((3, 320, 320)), dict(boxes=boxes, labels=torch.ones(2, dtype=torch.long))

    def __len__(self):
        return self.n


def collate_fn(batch):
    imgs, target = zip(*batch)
    return imgs, target


def _test_trainer(
    learner: Trainer,
    num_it: int,
    ref_param: str,
    freeze_until: Optional[str] = None,
    lr: float = 1e-3
) -> None:

    learner.save(learner.output_file)
    checkpoint = torch.load(learner.output_file, map_location='cpu')
    model_w = learner.model.state_dict()[ref_param].clone()
    # Check setup
    assert learner.check_setup(freeze_until, num_it=num_it)

    # LR Find
    learner.load(checkpoint)

    with pytest.raises(AssertionError):
        learner.plot_recorder(block=False)

    with pytest.raises(ValueError):
        learner.lr_find(freeze_until, num_it=num_it + 1)

    # Test norm weight decay
    learner.lr_find(freeze_until, norm_weight_decay=5e-4, num_it=num_it)
    assert len(learner.lr_recorder) == len(learner.loss_recorder)
    learner.plot_recorder(block=False)

    # Training
    # Perform the iterations
    learner.load(checkpoint)
    with pytest.raises(ValueError):
        learner.fit_n_epochs(1, 1e-3, freeze_until, sched_type='my_scheduler')
    learner.fit_n_epochs(1, 1e-3, freeze_until)
    # Check that params were updated
    assert not torch.equal(learner.model.state_dict()[ref_param], model_w)
    learner.load(checkpoint)
    learner.fit_n_epochs(1, 1e-3, freeze_until, sched_type='cosine')
    # Check that params were updated
    assert not torch.equal(learner.model.state_dict()[ref_param], model_w)


def test_classification_trainer(tmpdir_factory):

    folder = tmpdir_factory.mktemp("checkpoints")
    file_path = str(folder.join("tmp.pt"))

    num_it = 100
    batch_size = 8
    # Generate all dependencies
    model = nn.Sequential(nn.Conv2d(3, 32, 3), nn.ReLU(inplace=True),
                          GlobalAvgPool2d(flatten=True), nn.Linear(32, 5))
    train_loader = DataLoader(MockClassificationDataset(num_it * batch_size), batch_size=batch_size)
    optimizer = torch.optim.Adam(model.parameters())
    criterion = nn.CrossEntropyLoss()

    with pytest.raises(ValueError if torch.cuda.is_available() else AssertionError):
        trainer.ClassificationTrainer(model, train_loader, train_loader, criterion, optimizer, gpu=7)

    learner = trainer.ClassificationTrainer(model, train_loader, train_loader, criterion, optimizer,
                                            output_file=file_path, gpu=0 if torch.cuda.is_available() else None)

    _test_trainer(learner, num_it, '3.weight', None)
    # AMP
    learner = trainer.ClassificationTrainer(
        model, train_loader, train_loader, criterion, optimizer,
        output_file=file_path, gpu=0 if torch.cuda.is_available() else None, amp=True)
    _test_trainer(learner, num_it, '3.weight', None)


def test_classification_trainer_few_classes():

    num_it = 10
    batch_size = 8
    # Generate all dependencies
    model = nn.Sequential(nn.Conv2d(3, 32, 3), nn.ReLU(inplace=True),
                          GlobalAvgPool2d(flatten=True), nn.Linear(32, 3))
    train_loader = DataLoader(MockClassificationDataset(num_it * batch_size), batch_size=batch_size)
    optimizer = torch.optim.Adam(model.parameters())
    criterion = nn.CrossEntropyLoss()
    learner = trainer.ClassificationTrainer(model, train_loader, train_loader, criterion, optimizer)
    # Fewer than 5 classes
    assert learner.evaluate()['acc5'] == 0


def test_binary_classification_trainer():

    num_it = 10
    batch_size = 8
    # Generate all dependencies
    model = nn.Sequential(nn.Conv2d(3, 32, 3), nn.ReLU(inplace=True),
                          GlobalAvgPool2d(flatten=True), nn.Linear(32, 1))
    train_loader = DataLoader(MockBinaryClassificationDataset(num_it * batch_size), batch_size=batch_size)
    optimizer = torch.optim.Adam(model.parameters())
    criterion = nn.BCEWithLogitsLoss()

    learner = trainer.BinaryClassificationTrainer(model, train_loader, train_loader, criterion, optimizer)

    res = learner.evaluate()
    assert 0 <= res['acc'] <= 1


def test_segmentation_trainer(tmpdir_factory):

    folder = tmpdir_factory.mktemp("checkpoints")
    file_path = str(folder.join("tmp.pt"))

    num_it = 100
    batch_size = 8
    # Generate all dependencies
    model = nn.Sequential(nn.Conv2d(3, 32, 3, padding=1), nn.ReLU(inplace=True), nn.Conv2d(32, 5, 3, padding=1))
    train_loader = DataLoader(MockSegDataset(num_it * batch_size), batch_size=batch_size)
    optimizer = torch.optim.Adam(model.parameters())
    criterion = nn.CrossEntropyLoss()

    learner = trainer.SegmentationTrainer(model, train_loader, train_loader, criterion, optimizer, num_classes=5,
                                          output_file=file_path, gpu=0 if torch.cuda.is_available() else None)

    _test_trainer(learner, num_it, '2.weight', None)
    # AMP
    learner = trainer.SegmentationTrainer(
        model, train_loader, train_loader, criterion, optimizer, num_classes=5,
        output_file=file_path, gpu=0 if torch.cuda.is_available() else None, amp=True)
    _test_trainer(learner, num_it, '2.weight', None)


def test_detection_trainer(tmpdir_factory):

    folder = tmpdir_factory.mktemp("checkpoints")
    file_path = str(folder.join("tmp.pt"))

    num_it = 10
    batch_size = 2
    # Generate all dependencies
    model = fasterrcnn_mobilenet_v3_large_320_fpn(pretrained_backbone=True, num_classes=10)
    train_loader = DataLoader(MockDetDataset(num_it * batch_size), batch_size=batch_size, collate_fn=collate_fn)
    optimizer = torch.optim.Adam(model.parameters())

    learner = trainer.DetectionTrainer(model, train_loader, train_loader, None, optimizer,
                                       output_file=file_path, gpu=0 if torch.cuda.is_available() else None)

    _test_trainer(learner, num_it, 'roi_heads.box_predictor.cls_score.weight', 'backbone', 5e-4)
    # AMP
    learner = trainer.DetectionTrainer(
        model, train_loader, train_loader, None, optimizer,
        output_file=file_path, gpu=0 if torch.cuda.is_available() else None, amp=True)
    _test_trainer(learner, num_it, 'roi_heads.box_predictor.cls_score.weight', 'backbone', 5e-4)
