"""Synthetic marker layouts: a green patch must never hide a red star elsewhere."""
import unittest
from PIL import Image,ImageDraw
from gift_recognition import colour_verdict
from summary_check import load_config


class StarGuardTests(unittest.TestCase):
    def test_both_layouts_veto_normal_even_when_primary_patch_is_green(self):
        config=load_config()['colour']
        for box in ((47,188,53,194),(60,185,66,191)):
            image=Image.new('RGB',(320,240),(129,242,74))
            ImageDraw.Draw(image).rectangle((box[0],box[1],box[2]-1,box[3]-1),fill=(210,55,15))
            result=colour_verdict(image,config)
            self.assertEqual(result['verdict'],'shiny')
            self.assertTrue(result['star_evidence']['candidate'])

    def test_partial_red_marker_is_unknown_instead_of_normal(self):
        image=Image.new('RGB',(320,240),(129,242,74));image.putpixel((49,191),(210,55,15))
        result=colour_verdict(image,load_config()['colour'])
        self.assertEqual(result['verdict'],'unknown')

    def test_red_outside_the_marker_band_does_not_mimic_a_star(self):
        image=Image.new('RGB',(320,240),(129,242,74))
        ImageDraw.Draw(image).rectangle((10,110,30,130),fill='red')
        result=colour_verdict(image,load_config()['colour'])
        self.assertEqual(result['verdict'],'normal')
        self.assertEqual(result['star_evidence']['red_pixels'],0)


if __name__=='__main__':unittest.main()
