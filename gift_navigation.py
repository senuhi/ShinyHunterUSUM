"""Japanese menu/party navigation anchors. No control or colour authorization."""
import json
from pathlib import Path
from PIL import Image,ImageStat
from gift_recognition import template_score,red_star_evidence

ROOT=Path(__file__).parent/'templates/ja/Navigation'


class NavigationAnchors:
    def __init__(self):
        self.config=json.loads((ROOT/'manifest.json').read_text())
        self.templates={}
        for state,items in self.config['states'].items():
            self.templates[state]=[]
            for item in items:
                with Image.open(ROOT/item['template']) as image:
                    self.templates[state].append((item['box'],image.convert('L')))

    def identify(self,image):
        scores={state:[template_score(image,box,reference,vertical=1)
                       if ImageStat.Stat(image.crop(box).convert('L')).stddev[0]>=5 else 1.0
                       for box,reference in templates]
                for state,templates in self.templates.items()}
        matches=[state for state,values in scores.items() if all(v<=self.config['threshold'] for v in values)]
        return (matches[0] if len(matches)==1 else 'unknown'),scores

    @staticmethod
    def map_score(image,reference):
        # Red Rotom frame geometry survives both dimming and eye colour changes.
        # Use colour ratios rather than brightness, which varies during dialogue.
        values=[]
        for box in ([0,0,40,125],[278,0,320,125]):
            def mask(part):
                raw=part.convert('RGB').tobytes()
                return [r>=15 and r>1.4*g and r>1.4*b for r,g,b in zip(raw[0::3],raw[1::3],raw[2::3])]
            a=mask(image.crop(box));b=mask(reference.crop(box))
            if sum(b)<len(b)*.1:return 1.0
            values.append(sum(x!=y for x,y in zip(a,b))/len(b))
        return max(values)

    @staticmethod
    def cursor(image):
        # The selected party card has a red arrow/border at these two positions.
        # These are UI cursor pixels, independent of the shiny marker band.
        counts=[red_star_evidence(image,box)['red_pixels']
                for box in ([0,29,16,49],[170,45,186,65])]
        selected=0
        if counts[0]>=15 and counts[0]-counts[1]>=12:selected=1
        if counts[1]>=15 and counts[1]-counts[0]>=12:selected=2
        return selected,counts
