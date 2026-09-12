import unittest
from album_v2.sign_off import TRACKS as SIGN
from album_v2.quiet_hours import TRACKS as QUIET
from album_v2.render import quiet_events, legacy_rain, SR

class AlbumScoreTests(unittest.TestCase):
    def test_sign_off_has_varied_forms_and_damage(self):
        self.assertEqual(len(SIGN),12)
        self.assertEqual(len({s['title'] for s in SIGN}),12)
        self.assertEqual(len({tuple((v[1],v[2],v[4]) for v in s['form']) for s in SIGN}),12)
        self.assertEqual(sum(s['warble']>=.007 for s in SIGN),2)
        self.assertGreaterEqual(sum(all(v[4]=='none' for v in s['form']) for s in SIGN),3)
        for s in SIGN:
            self.assertEqual(len(s['a']),len(s['bass']))
            self.assertEqual(len(s['b']),len(s['bass_b']))
            for phrase in [s['motif'],s['answer']]:
                for bar,beat,pitch,duration in phrase:
                    self.assertGreaterEqual(bar,0);self.assertTrue(0<=beat<4)
                    self.assertTrue(0<=pitch<=127);self.assertGreater(duration,0)

    def test_piano_events_have_unique_matched_voices_inside_render(self):
        self.assertEqual(len(QUIET),12)
        for s in QUIET:
            events,seconds=legacy_rain() if s.get('legacy') else quiet_events(s)
            for part,ev in events.items():
                ons={e[5]:e for e in ev if e[1]=='on'}
                offs={e[5]:e for e in ev if e[1]=='off'}
                self.assertEqual(len(ons),len(ev)//2)
                self.assertEqual(set(ons),set(offs))
                for uid,on in ons.items():
                    off=offs[uid]
                    self.assertLess(on[0],off[0]);self.assertLess(off[0],seconds*SR)
                    self.assertGreaterEqual(on[0],0);self.assertTrue(0<on[4]<=127)
                    self.assertEqual(on[2:4],off[2:4]);self.assertTrue(0<=on[3]<=127)

if __name__=='__main__':unittest.main()
