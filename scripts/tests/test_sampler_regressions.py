import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from music_engine.samplers import ExsSampler, DrumSampler, _pcm_to_float


class SamplerRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)
        self.manifest = [dict(file='test.wav', root=60, keylo=0, keyhi=127, vello=1, velhi=127)]
        (self.path/'manifest.json').write_text(json.dumps(self.manifest))

    def tearDown(self):
        self.tmp.cleanup()

    def sampler(self, **kwargs):
        return ExsSampler(str(self.path), sample_rate=1000, release=0, deterministic=True, **kwargs)

    def test_legacy_overlapping_retriggers_keep_both_voices(self):
        wavfile.write(self.path/'test.wav', 1000, np.ones(500, np.float32))
        events=[(0,'on',0,60,127),(50,'on',0,60,127),(100,'off',0,60,0),(150,'off',0,60,0)]
        x=self.sampler().render(events,.2)
        np.testing.assert_allclose(x[10:50],1)
        np.testing.assert_allclose(x[50:100],2)
        np.testing.assert_allclose(x[100:150],1)

    def test_explicit_voice_ids_pair_nested_overlaps(self):
        wavfile.write(self.path/'test.wav', 1000, np.ones(500, np.float32))
        events=[(0,'on',0,60,127,'a'),(50,'on',0,60,127,'b'),(75,'off',0,60,0,'b'),(150,'off',0,60,0,'a')]
        x=self.sampler().render(events,.2)
        self.assertEqual(x[25],1); self.assertEqual(x[60],2); self.assertEqual(x[100],1)

    def test_stereo_and_source_rate_preserved(self):
        t=np.arange(500)/2000
        data=np.stack([np.sin(2*np.pi*100*t),np.zeros_like(t)],axis=1).astype(np.float32)
        wavfile.write(self.path/'test.wav',2000,data)
        x=self.sampler(stereo_output=True).render([(0,'on',0,60,127),(300,'off',0,60,0)],.4)
        self.assertEqual(x.shape,(2,400))
        self.assertLess(np.max(abs(x[1])),1e-6)
        freq=np.fft.rfftfreq(200,1/1000)[np.argmax(abs(np.fft.rfft(x[0,20:220])))]
        self.assertEqual(freq,100)
        self.assertLess(np.max(abs(x[:,260:])),1e-6)
        drum=DrumSampler(str(self.path),sample_rate=1000).render([(0,'on',9,0,127)],.4)
        self.assertLess(np.max(abs(drum[:,260:])),1e-6)

    def test_drum_zero_velocity_is_silent_and_negative_time_rejected(self):
        wavfile.write(self.path/'test.wav',1000,np.ones(500,np.float32))
        drum=DrumSampler(str(self.path),sample_rate=1000)
        np.testing.assert_array_equal(drum.render([(0,'on',9,0,0)],.1),0)
        with self.assertRaises(ValueError):drum.render([(-1,'on',9,0,127)],.1)

    def test_unsigned_pcm_silence(self):
        np.testing.assert_array_equal(_pcm_to_float(np.array([0,128,255],np.uint8)),[-1,0,127/128])

    def test_velocity_zero_and_missing_off(self):
        wavfile.write(self.path/'test.wav',1000,np.ones(500,np.float32))
        x=self.sampler().render([(0,'on',0,60,127),(50,'on',0,60,0)],.1)
        self.assertEqual(x[25],1); self.assertEqual(x[75],0)
        self.assertEqual(self.sampler().render([(0,'on',0,60,127)],.1)[-1],1)

class ExternalRendererTests(unittest.TestCase):
    def test_external_helper_preserves_rate_channels_and_unsigned_silence(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from music_engine.renderers import render_external_instrument
        import sys
        def fake_run(command, **kwargs):
            wavfile.write(command[-1], 2000, np.full((400,2),128,np.uint8))
            return SimpleNamespace(returncode=0,stdout='',stderr='')
        with patch('music_engine.renderers.subprocess.run',side_effect=fake_run):
            x=render_external_instrument([{'note':60}],.3,python_path=sys.executable,
                helper_path='helper.py',sample_rate=1000)
        self.assertEqual(x.shape,(2,300))
        np.testing.assert_array_equal(x,0)

    def test_external_helper_converts_rate_before_padding(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from music_engine.renderers import render_external_instrument
        import sys
        def fake_run(command, **kwargs):
            t=np.arange(400)/2000
            x=np.stack([np.sin(2*np.pi*100*t),np.zeros_like(t)],axis=1).astype(np.float32)
            wavfile.write(command[-1],2000,x)
            return SimpleNamespace(returncode=0,stdout='',stderr='')
        with patch('music_engine.renderers.subprocess.run',side_effect=fake_run):
            x=render_external_instrument([{'note':60}],.3,python_path=sys.executable,
                helper_path='helper.py',sample_rate=1000)
        freq=np.fft.rfftfreq(100,1/1000)[np.argmax(abs(np.fft.rfft(x[0,50:150])))]
        self.assertEqual(freq,100)
        np.testing.assert_array_equal(x[1],0)
        np.testing.assert_array_equal(x[:,210:],0)

if __name__=='__main__': unittest.main()
