import unittest
import inspect
import torch
from holocron.nn import functional as F
from holocron.nn.modules import activation, loss


class Tester(unittest.TestCase):

    def _test_activation_function(self, name, input_shape):
        fn = F.__dict__[name]

        # Optional testing
        fn_args = inspect.signature(fn).parameters.keys()
        cfg = {}
        if 'inplace' in fn_args:
            cfg['inplace'] = [False, True]

        # Generate inputs
        x = torch.rand(input_shape)

        # Optional argument testing
        kwargs = {}
        for inplace in cfg.get('inplace', [None]):
            if isinstance(inplace, bool):
                kwargs['inplace'] = inplace
            out = fn(x, **kwargs)
            self.assertEqual(out.size(), x.size())
            if kwargs.get('inplace', False):
                self.assertEqual(x.data_ptr(), out.data_ptr())

    def _test_loss_function(self, name):

        num_batches = 2
        num_classes = 4
        # 4 classes
        x = torch.ones(num_batches, num_classes, 20, 20)
        x[:, 0, ...] = 10

        # Identical target
        target = torch.zeros((num_batches, 20, 20), dtype=torch.long)
        loss_fn = F.__dict__[name]
        self.assertAlmostEqual(loss_fn(x, target).item(), 0)
        self.assertTrue(torch.allclose(loss_fn(x, target, reduction='none'),
                                       torch.zeros((num_batches, 20, 20), dtype=x.dtype)))

    def _test_activation_module(self, name, input_shape):
        module = activation.__dict__[name]

        # Optional testing
        fn_args = inspect.signature(module).parameters.keys()
        cfg = {}
        if 'inplace' in fn_args:
            cfg['inplace'] = [False, True]

        # Generate inputs
        x = torch.rand(input_shape)

        # Optional argument testing
        kwargs = {}
        for inplace in cfg.get('inplace', [None]):
            if isinstance(inplace, bool):
                kwargs['inplace'] = inplace
            out = module(**kwargs)(x)
            self.assertEqual(out.size(), x.size())
            if kwargs.get('inplace', False):
                self.assertEqual(x.data_ptr(), out.data_ptr())

    def _test_loss_module(self, name):

        num_batches = 2
        num_classes = 4
        # 4 classes
        x = torch.ones(num_batches, num_classes, 20, 20)
        x[:, 0, ...] = 10

        # Identical target
        target = torch.zeros((num_batches, 20, 20), dtype=torch.long)
        criterion = loss.__dict__[name]()
        self.assertAlmostEqual(criterion(x, target).item(), 0)
        criterion = loss.__dict__[name](reduction='none')
        self.assertTrue(torch.allclose(criterion(x, target),
                                       torch.zeros((num_batches, 20, 20), dtype=x.dtype)))


act_fns = ['mish', 'nl_relu']

for fn_name in act_fns:
    def do_test(self, fn_name=fn_name):
        input_shape = (32, 3, 224, 224)
        self._test_activation_function(fn_name, input_shape)

    setattr(Tester, "test_" + fn_name, do_test)

act_fns = ['focal_loss']

for fn_name in act_fns:
    def do_test(self, fn_name=fn_name):
        self._test_loss_function(fn_name)

    setattr(Tester, "test_" + fn_name, do_test)

act_modules = ['Mish', 'NLReLU']

for mod_name in act_modules:
    def do_test(self, mod_name=mod_name):
        input_shape = (32, 3, 224, 224)
        self._test_activation_module(mod_name, input_shape)

    setattr(Tester, "test_" + mod_name, do_test)


loss_modules = ['FocalLoss']

for mod_name in loss_modules:
    def do_test(self, mod_name=mod_name):
        self._test_loss_module(mod_name)

    setattr(Tester, "test_" + mod_name, do_test)


if __name__ == '__main__':
    unittest.main()
