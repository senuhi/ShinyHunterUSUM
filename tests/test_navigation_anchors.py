"""Template navigation rejects blank/ambiguous controls; cursor is independent."""
import unittest
from PIL import Image,ImageDraw,ImageEnhance
from gift_navigation import NavigationAnchors,ROOT


class NavigationAnchorTests(unittest.TestCase):
    def setUp(self):self.nav=NavigationAnchors()

    def fixture(self,state):
        image=Image.new('RGB',(320,240),(40,120,90))
        for item in self.nav.config['states'][state]:
            with Image.open(ROOT/item['template']) as part:image.paste(part,item['box'][:2])
        return image

    def test_requires_two_textured_anchors_not_similar_background(self):
        for state in ('menu','party'):
            image=self.fixture(state)
            self.assertEqual(self.nav.identify(image)[0],state)
            box=self.nav.config['states'][state][0]['box'];image.paste((60,100,130),box)
            self.assertEqual(self.nav.identify(image)[0],'unknown')
        for colour in ('#406080','#81f24a','black','white'):
            self.assertEqual(self.nav.identify(Image.new('RGB',(320,240),colour))[0],'unknown')

    def test_cursor_requires_a_dominant_marker_and_rejects_ambiguity(self):
        image=self.fixture('party');draw=ImageDraw.Draw(image)
        self.assertEqual(self.nav.cursor(image)[0],0)
        draw.rectangle((3,32,11,42),fill=(230,35,20))
        self.assertEqual(self.nav.cursor(image)[0],1)
        draw.rectangle((173,48,181,58),fill=(230,35,20))
        self.assertEqual(self.nav.cursor(image)[0],0)
        draw.rectangle((3,32,11,42),fill=(40,120,90))
        self.assertEqual(self.nav.cursor(image)[0],2)

    def test_map_mask_survives_dimming_but_rejects_menus(self):
        with Image.open(ROOT.parent/'Diagnostics/field_hud.png') as hud:
            field=Image.new('RGB',(320,240));field.paste(hud,(0,0))
        self.assertLess(self.nav.map_score(ImageEnhance.Brightness(field).enhance(.25),field),.13)
        self.assertGreater(self.nav.map_score(self.fixture('menu'),field),.13)
        self.assertGreater(self.nav.map_score(self.fixture('party'),field),.13)


if __name__=='__main__':unittest.main()
