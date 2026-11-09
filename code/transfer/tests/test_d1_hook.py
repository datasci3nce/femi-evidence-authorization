import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'src'))
try:
 import torch
except ImportError:
 torch=None
from d1_local import Hook

@unittest.skipUnless(torch is not None,'torch not installed; optional GPU test not relevant offline')
class HookTests(unittest.TestCase):
 def test_native_tensor_capture_patch_and_stop(self):
  class Mock(torch.nn.Module):
   def __init__(self):
    super().__init__();self.encoder=torch.nn.Linear(4,4,bias=False)
   def forward(self,x):return self.encoder(x)
  model=Mock();hook=Hook(model,'encoder',torch)
  x=torch.ones((1,3,4));hook.start()
  before=model(x);observed=hook.stop()
  self.assertEqual(tuple(observed.shape),(4,))
  vec=torch.ones(4)
  hook.start(vec,0.5);after=model(x);hook.stop(expected_patched=True)
  self.assertTrue(torch.allclose(after[:,-1,:]-before[:,-1,:],torch.full((1,4),0.5)))
  self.assertTrue(torch.allclose(after[:,0,:],before[:,0,:]))
  hook.close()
 def test_mismatched_tensor_shape_fails_closed(self):
  class Bad(torch.nn.Module):
   def __init__(self):super().__init__();self.linear=torch.nn.Linear(4,4)
   def forward(self,x):return self.linear(x)
  model=Bad();hook=Hook(model,'linear',torch);hook.start()
  with self.assertRaises(RuntimeError): model(torch.ones(1,4))
  hook.close()
if __name__=='__main__':unittest.main()
